import os
from dotenv import load_dotenv
from crewai import Agent, LLM
from crewai_tools import SerperDevTool

load_dotenv()

# NVIDIA NIM via OpenAI-compatible endpoint
llm = LLM(
    provider="openai",
    model="meta/llama-3.1-8b-instruct",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.2,
)
llm_2 = LLM(
    provider="openai",
    model="nvidia/nemotron-3-nano-30b-a3b",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.2,
)
llm_3 = LLM(
    provider="openai",
    model="qwen/qwen3-next-80b-a3b-instruct",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.2,
)

search_tool = SerperDevTool()

research_agent = Agent(
    role="Research Specialist",
    goal="Search the web and collect factual information with sources",
    backstory="Expert web researcher",
    tools=[search_tool],
    llm=llm,
    verbose=False
)

analysis_agent = Agent(
    role="Data Analyst",
    goal="Analyze research data and extract key insights",
    backstory="You turn raw information into insights",
    llm=llm,
    verbose=False
)

structuring_agent = Agent(
    role="Report Architect",
    goal="Organize the insights into a professional report structure",
    backstory="You design clean, logical report outlines",
    llm=llm,
    verbose=False
)

writing_agent = Agent(
    role="Conversational AI Assistant",
    goal="Provide clear, concise, and conversational answers like ChatGPT - avoid formal reports unless specifically requested",
    backstory="You are a friendly, knowledgeable AI assistant that explains things in simple, easy-to-understand language. You keep answers focused and interactive, not overly formal or lengthy.",
    llm=llm,
    verbose=False
)
