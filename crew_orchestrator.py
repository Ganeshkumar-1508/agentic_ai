# crew_orchestrator.py
from crewai import Crew, Task
from crew_agents import text_agent, image_agent, get_tts_agent
import re
import uuid as uuid_module
import os 
from services.tts_service import generate_speech

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

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
    text_task = None
    
    # 1️⃣ Build tasks
    for step in plan["steps"]:
        if step["agent"] == "TEXT":
            text_task = Task(
                description=step["input"],
                agent=text_agent,
                expected_output="Final user-facing text only",
            )
            tasks.append(text_task)
        elif step["agent"] == "IMAGE":
            tasks.append(
                Task(
                    description=step["input"],
                    agent=image_agent,
                    expected_output="Image file path",
                )
            )

    # 2️⃣ Run Crew
    print("🚀 CREW KICKOFF STARTING...")
    crew = Crew(
        agents=[text_agent, image_agent],
        tasks=tasks,
        process="sequential",
        verbose=False,
    )
    crew.kickoff()
    print("🚀 CREW KICKOFF COMPLETED")

    # 3️⃣ Collect outputs
    text_parts = []
    image_paths = []
    
    for i, task in enumerate(tasks):
        if task is text_task:
            output = _extract_raw(task.output)
            if output:
                text_parts.append(output)
        else:
            output = _extract_raw(task.output)
            if output.startswith("generated_images/"):
                image_paths.append(output)
            elif output:
                text_parts.append(output)

    final_text = "\n\n".join(text_parts)
    final_text = clean_text_for_ui(final_text)
    
    # 4️⃣ 🔊 RUN TTS
    audio_path = None
    
    if final_text:
        print("🔊 ========== TTS EXECUTION STARTING ==========")
        
        tts_input_filename = f"tts_input_{str(uuid_module.uuid4())[:8]}.txt"
        tts_input_filepath = os.path.join(AUDIO_DIR, tts_input_filename)
        
        # ✅ DEBUG: Log text being saved
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