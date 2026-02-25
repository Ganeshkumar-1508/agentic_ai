# tools/tts_tool.py
from crewai.tools import tool
from services.tts_service import generate_speech

@tool("text_to_speech")
def text_to_speech_tool(text: str) -> str:
    """
    Converts final user-facing text into speech.
    """
    print("🔥 TTS TOOL CALLED")
    print("📝 TEXT PREVIEW:", text[:100])

    return generate_speech(text)