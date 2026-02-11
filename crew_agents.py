from crewai import Agent
from crewai.llm import LLM
import os

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
