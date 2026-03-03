# tools/tts_tool.py
from crewai.tools import tool
from services.tts_service import generate_speech
import services.tts_service
import time
import os

print("🔥🔥🔥 TTS SERVICE IMPORTED FROM:", services.tts_service.__file__)

call_count = 0

@tool("text_to_speech")
def text_to_speech_tool(text: str) -> str:
    """
    Converts text into speech.
    Accepts a path to a text file OR raw text.
    """
    global call_count
    call_count += 1
    
    timestamp = time.time()
    print(f"\n🔥 TTS TOOL CALLED [Call #{call_count}, Time: {timestamp}]")
    print(f"📝 INPUT PREVIEW: {text[:100]}...")
    
    input_text = text
    file_path = text.strip()
    
    is_likely_path = file_path.startswith("generated_audio") and file_path.endswith(".txt")

    if is_likely_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        potential_path = os.path.join(base_dir, file_path)
        
        if os.path.exists(potential_path):
            print(f"📂 Detected FILE INPUT: {potential_path}")
            try:
                with open(potential_path, "r", encoding="utf-8") as f:
                    input_text = f.read()
                # ✅ DEBUG: Log file content length
                print(f"📖 Read {len(input_text)} chars from file")
                print(f"📝 File Content Preview: {input_text[:150]}...")
            except Exception as e:
                print(f"❌ Failed to read file: {e}")
                return f"ERROR: Failed to read file {file_path}"
        else:
            print(f"❌ File NOT FOUND: {potential_path}")
            return f"ERROR: File not found: {file_path}. Do not invent filenames."
    else:
        print(f"📝 Detected RAW TEXT INPUT ({len(text)} chars)")

    if not input_text.strip():
        return "ERROR: No text provided to TTS"
    
    try:
        result = generate_speech(input_text)
        print(f"✅ TTS TOOL SUCCESS: Returned {result}")
        return result
    except Exception as e:
        print(f"❌ TTS TOOL EXCEPTION: {str(e)[:100]}")
        raise