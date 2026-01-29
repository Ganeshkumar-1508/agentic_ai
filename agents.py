import os
from dotenv import load_dotenv
from crewai import Agent, LLM
from crewai_tools import SerperDevTool

load_dotenv()

llm = LLM(
    provider="openai",
    model="meta/llama-3.1-8b-instruct",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.2,
)
# llm_2 = LLM(
#     provider="openai",
#     model="nvidia/nemotron-3-nano-30b-a3b",
#     api_key=os.getenv("OPENAI_API_KEY"),
#     base_url=os.getenv("OPENAI_BASE_URL"),
#     temperature=0.2,
# )
# llm_3 = LLM(
#     provider="openai",
#     model="qwen/qwen3-next-80b-a3b-instruct",
#     api_key=os.getenv("OPENAI_API_KEY"),
#     base_url=os.getenv("OPENAI_BASE_URL"),
#     temperature=0.2,
#     max_tokens=1000
# )

search_tool = SerperDevTool()

research_agent = Agent(
    role="Research Specialist",
    goal="Search the web and collect factual information with sources",
    backstory="Expert web researcher",
    tools=[search_tool],
    llm=llm,
    verbose=True
)

analysis_agent = Agent(
    role="Data Analyst",
    goal="Analyze research data and extract key insights",
    backstory="You turn raw information into insights",
    llm=llm,
    verbose=True
)

structuring_agent = Agent(
    role="Report Architect",
    goal="Organize the insights into a professional report structure",
    backstory="You design clean, logical report outlines",
    llm=llm,
    verbose=True
)

writing_agent = Agent(
    role="Technical Writer",
    goal="Write a clear and professional final report",
    backstory="You write concise, high quality reports",
    llm=llm,
    verbose=True
)

code_research_agent = Agent(
    role="Code Researcher",
    goal="Search the web for official documentation and best practices",
    backstory=(
        "You search trusted documentation and APIs. "
        "You summarize findings for internal use only. "
        "You NEVER output code."
    ),
    tools=[search_tool],   # reusing existing Serper tool
    llm=llm,               # reusing existing LLM
    verbose=True
)

code_agent = Agent(
    role="Code Generator",
    goal="Generate executable code ONLY",
    backstory=(
        "You output ONLY executable code. "
        "No explanations. "
        "No markdown. "
        "No extra text."
    ),
    llm=llm,
    verbose=True
)
