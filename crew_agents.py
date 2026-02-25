from crewai import Agent
from crewai.llm import LLM
import os
from tools.image_generation_tool import ImageGenerationTool
from tools.tts_tool import text_to_speech_tool

# 🔥 Explicit NVIDIA LLM
nim_llm = LLM(
    provider="nvidia",
    model=os.getenv("LITELLM_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL"),
)

text_agent = Agent(
    role="Text Generation Agent",
    goal="Generate high-quality text such as explanations, code, and reports",
    backstory="Handles all text-based generation",
    allow_delegation=False,
    llm=nim_llm
)

tts_agent = Agent(
    role="Text to Speech Executor",
    goal="Call the text_to_speech tool with the provided text and return the tool output.",
    backstory=(
        "You MUST call the Text to Speech tool. "
        "You are NOT allowed to answer in text. "
        "You MUST return ONLY the tool output."
    ),
    tools=[text_to_speech_tool],
    allow_delegation=False,
    llm=nim_llm,
    verbose=False
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
