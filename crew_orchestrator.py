from crewai import Crew, Task
from crew_agents import text_agent, data_agent, image_agent, vision_agent, get_tts_agent
import pandas as pd
from io import StringIO
import plotly.express as px
import uuid
import uuid as uuid_module
import os
import re
import base64
import requests as http_requests
from services.tts_service import generate_speech

OUTPUT_DIR = "generated_charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

def contains_numeric_data(text: str) -> bool:
    numbers = re.findall(r"\d+\.?\d*", text)
    return len(numbers) >= 2


def render_chart(df, user_query):
    numeric_cols = df.select_dtypes(include='number').columns
    x_col = df.columns[0]
    lower_query = user_query.lower()

    # If user explicitly asks for bar
    if "bar" in lower_query:
        fig = px.bar(df, x=x_col, y=numeric_cols)

    # If explicitly line
    elif "line" in lower_query:
        fig = px.line(df, x=x_col, y=numeric_cols)

    # Auto fallback
    else:
        if len(numeric_cols) == 1:
            fig = px.bar(df, x=x_col, y=numeric_cols[0])
        else:
            fig = px.line(df, x=x_col, y=numeric_cols)

    filename = f"{uuid.uuid4()}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    fig.write_image(path)
    return path


def analyse_image_with_vision_llm(image_b64: str, media_type: str, user_query: str) -> str:
    """
    Call the multimodal LLM directly via its HTTP endpoint so we can pass
    image data as a base64-encoded vision message.

    Falls back to a crewai Task approach if the environment variable
    VISION_DIRECT_URL is not set (i.e. the model supports vision through the
    same LiteLLM proxy that crew_agents already uses).
    """
    import os

    api_key = os.getenv("NVIDIA_API_KEY", "")
    base_url = os.getenv("LITELLM_BASE_URL", "").rstrip("/")
    model = os.getenv("VISION_MODEL", os.getenv("LITELLM_MODEL", ""))


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": user_query if user_query else "Describe this image in detail."
                    }
                ]
            }
        ],
        "max_tokens": 1024
    }

    try:
        resp = http_requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        # Fallback: save image to disk and pass path in text prompt 

        print(f"[VISION] Direct multimodal call failed ({e}), falling back to text description.")

        # Save image temporarily so we can at least reference it
        os.makedirs("generated_images", exist_ok=True)
        temp_path = os.path.join("generated_images", f"uploaded_{uuid.uuid4()}.png")
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(image_b64))

        fallback_task = Task(
            description=(
                f"The user has uploaded an image saved at: {temp_path}\n"
                f"User question: {user_query}\n\n"
                "Acknowledge that image analysis requires a vision-capable model and "
                "provide as much helpful context as you can based on the question alone."
            ),
            agent=vision_agent,
            expected_output="Helpful textual response about the image or question."
        )
        crew = Crew(
            agents=[vision_agent],
            tasks=[fallback_task],
            process="sequential",
            verbose=False
        )
        result = crew.kickoff()
        return str(result).strip()

def _extract_raw(task_output) -> str:
    if hasattr(task_output, "raw"):
        return (task_output.raw or "").strip()
    return str(task_output).strip()

def clean_text_for_ui(text: str) -> str:
    # Remove Setext headers
    text = re.sub(r"^\s*={3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.MULTILINE)
    
    # Remove Bold/Italic
    text = text.replace("**", "").replace("__", "")
    
    # Clean whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def run_crew(plan: dict, user_query: str):
    print("\n🔍 ========== CREW START ==========")
    
    tasks = []
    text_outputs = []
    image_paths = []
    text_task = None

    
    
    for step in plan["steps"]:

        if step["agent"] == "VISION":
            image_b64 = step.get("image_b64", "")
            media_type = step.get("image_media_type", "image/jpeg")
            query = step.get("input", user_query)

            result_text = analyse_image_with_vision_llm(image_b64, media_type, query)
            if result_text:
                text_outputs.append(result_text)


        elif step["agent"] == "DATA":

            data_task = Task(
                description=(
                    step["input"]
                    + "\n\nExtract structured numeric data.\n"
                    + "Return ONLY CSV.\n"
                    + "No markdown.\n"
                    + "First row must be headers."
                ),
                agent=data_agent,
                expected_output="Raw CSV only"
            )

            crew = Crew(
                agents=[data_agent],
                tasks=[data_task],
                process="sequential",
                verbose=False
            )

            result = crew.kickoff()
            raw_csv = str(result).strip()

            try:
                df = pd.read_csv(StringIO(raw_csv))
                chart_path = render_chart(df, user_query)
                image_paths.append(chart_path)

            except Exception as e:
                text_outputs.append(
                    f"⚠️ Failed to generate chart from data: {str(e)}"
                )


        
        elif step["agent"] == "TEXT":

            text_task = Task(
                description=step["input"],
                agent=text_agent,
                expected_output="High-quality text output"
            )

            crew = Crew(
                agents=[text_agent],
                tasks=[text_task],
                process="sequential",
                verbose=False
            )

            result = crew.kickoff()

            if result:
                text_outputs.append(str(result).strip())

    
        
        elif step["agent"] == "IMAGE":

            image_task = Task(
                description=step["input"],
                agent=image_agent,
                expected_output="Image file path"
            )

            crew = Crew(
                agents=[image_agent],
                tasks=[image_task],
                process="sequential",
                verbose=False
            )

            result = crew.kickoff()

            if result:
                path = str(result).strip()

                if path.endswith(".png") or path.endswith(".jpg"):
                    image_paths.append(path)
                else:
                    text_outputs.append(path)

    
    #text_parts = []
    #image_paths = []
    
    #for i, task in enumerate(tasks):
    #    if task is text_task:
    #        output = _extract_raw(task.output)
    #        if output:
    #            text_parts.append(output)
    #    else:
    #        output = _extract_raw(task.output)
    #        if output.startswith("generated_images/"):
    #            image_paths.append(output)
    #        elif output:
    #            text_parts.append(output)

    final_text = "\n\n".join(text_outputs)
    final_text = clean_text_for_ui(final_text)
    
    # RUN TTS
    audio_path = None
    
    if final_text:
        print("🔊 ========== TTS EXECUTION STARTING ==========")
        
        tts_input_filename = f"tts_input_{str(uuid_module.uuid4())[:8]}.txt"
        tts_input_filepath = os.path.join(AUDIO_DIR, tts_input_filename)
        
        # Log text being saved
        print(f"💾 Saving TTS text to: {tts_input_filepath}")
        
        with open(tts_input_filepath, "w", encoding="utf-8") as f:
            f.write(final_text)
        
        relative_path = os.path.relpath(tts_input_filepath, BASE_DIR).replace("\\", "/")

        try:
            current_tts_agent = get_tts_agent()
            
            tts_task = Task(
                description=(
                    f"Generate audio for the text file located at: '{relative_path}'\n\n"
                    f"Instructions:\n"
                    f"1. Call the `text_to_speech` tool.\n"
                    f"2. Pass the exact string '{relative_path}' as the argument.\n"
                    f"3. Do not modify the path string."
                ),
                agent=current_tts_agent,
                expected_output="File path to the generated .wav audio",
            )
            
            tts_crew = Crew(
                agents=[current_tts_agent],
                tasks=[tts_task],
                process="sequential",
                verbose=False,
            )
            
            print(f"🚀 TTS CREW KICKOFF STARTING...")
            tts_crew.kickoff()
            print(f"🚀 TTS CREW KICKOFF COMPLETED")
            
            raw = _extract_raw(tts_task.output)
            print(f"📝 TTS Raw output: {raw[:150]}")
            
            # Extract path
            match = re.search(r'generated_audio[\\/][\w\-_.]+\.(?:wav|mp3)', raw)
            if match:
                candidate = match.group(0).replace("\\", "/")
                if os.path.exists(candidate):
                    audio_path = candidate
                    print(f"✅ Audio file EXISTS: {audio_path}")
                else:
                    print(f"❌ Audio file MISSING: {candidate}")
            else:
                print(f"❌ Audio path NOT found in TTS output")
        
        except Exception as crew_error:
            print(f"⚠️ TTS Crew failed: {str(crew_error)[:100]}")
            print("⚠️ Attempting direct fallback...")
            
            # Fallback
            try:
                audio_path = generate_speech(final_text)
                print(f"✅ Fallback TTS generated: {audio_path}")
            except Exception as direct_error:
                print(f"❌ Fallback TTS also failed: {str(direct_error)[:100]}")
        
        print("🔊 ========== TTS EXECUTION COMPLETED ==========\n")

    return {
        "text": final_text,
        "images": image_paths,
        "audio": audio_path,
    }