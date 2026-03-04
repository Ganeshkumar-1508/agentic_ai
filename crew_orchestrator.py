from crewai import Crew, Task
from crew_agents import text_agent, data_agent, image_agent, vision_agent
import pandas as pd
from io import StringIO
import plotly.express as px
import uuid
import os
import re
import base64
import requests as http_requests

OUTPUT_DIR = "generated_charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


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

    # ── Try direct OpenAI-compatible vision call ─────────────────────────────
    # Most NVIDIA NIM / LiteLLM endpoints accept the standard vision format.
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
        # ── Fallback: save image to disk and pass path in text prompt ────────
        # This works when the model does NOT support vision but the user still
        # wants *something* back.
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


def run_crew(plan: dict, user_query: str):

    tasks = []
    text_outputs = []
    image_paths = []

    
    # STEP 1: Execute steps sequentially
    
    for step in plan["steps"]:

        # ── VISION AGENT (user-uploaded image analysis) ──────────────────────
        if step["agent"] == "VISION":
            image_b64 = step.get("image_b64", "")
            media_type = step.get("image_media_type", "image/jpeg")
            query = step.get("input", user_query)

            result_text = analyse_image_with_vision_llm(image_b64, media_type, query)
            if result_text:
                text_outputs.append(result_text)


        # DATA AGENT → CSV → CHART

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


        # TEXT AGENT
        
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

    
        # IMAGE AGENT
        
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

    
    # FINAL RESPONSE

    return {
        "text": "\n\n".join(text_outputs),
        "images": image_paths
    }