from crewai import Agent
from crewai.llm import LLM
import os
from tools.image_generation_tool import ImageGenerationTool
from tools.tts_tool import text_to_speech_tool

# Explicit NVIDIA LLM
nim_llm = LLM(
    provider="nvidia",
    model=os.getenv("LITELLM_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL"),
    stop=["</s>"]
)

text_agent = Agent(
    role="Text Generation Agent",
    goal="Generate high-quality text such as explanations, code, and reports",
    backstory="Handles all text-based generation",
    allow_delegation=False,
    llm=nim_llm,
)

data_agent = Agent(
    role="Data Extraction Agent",
    goal="Extract structured numeric data from user prompts and return strict CSV only.",
    backstory=(
        "You analyze user input and extract structured numeric data. "
        "You must return ONLY raw CSV. No markdown. No explanations."
    ),
    allow_delegation=False,
    llm=nim_llm
) 
# FINAL: Factory function with clear instructions for file handling
def get_tts_agent():
    return Agent(
        role="TTS Tool Executor",
        goal="Convert text files into speech audio files",
        backstory=(
            "You are a tool executor. You have access to the `text_to_speech` tool. "
            "This tool is capable of reading text files from disk. "
            "You do NOT need to read the files yourself. "
            "When given a file path, simply pass that path to the `text_to_speech` tool. "
            "Trust that the tool will handle the file reading and audio generation."
        ),
        tools=[text_to_speech_tool],
        allow_delegation=False,
        llm=nim_llm,
        verbose=False,
        max_iter=1,
    )

image_agent = Agent(
    role="Image Generation Agent",
    goal="Generate high quality images based on user request",
    backstory="Expert visual AI generator using AI Horde API",
    tools=[ImageGenerationTool()],
    allow_delegation=False,
    llm=nim_llm,
    verbose=False
)


vision_llm = LLM(
    provider="nvidia",
    model=os.getenv("VISION_MODEL", os.getenv("LITELLM_MODEL")),
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL"),
    stop=["</s>"]
)

vision_agent = Agent(
    role="Vision Analysis Agent",
    goal="Analyse and describe images uploaded by the user, answering any questions about them",
    backstory=(
        "You are an expert visual analyst. You receive an image together with a user question "
        "and provide a detailed, accurate, and helpful textual response about the image content."
    ),
    allow_delegation=False,
    llm=vision_llm,
    verbose=False,
)