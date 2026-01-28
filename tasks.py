from crewai import Task
from agents import research_agent, analysis_agent, structuring_agent, writing_agent

research_task = Task(
    description="Search the web for the user's query: {topic}",
    expected_output="Raw web data",
    agent=research_agent
)

analysis_task = Task(
    description="Analyze and extract only relevant information from research data",
    expected_output="Filtered insights",
    agent=analysis_agent
)

structuring_task = Task(
    description="""
    Determine the SINGLE correct output type based on intent: {intent}

    Allowed values:
    - CODE
    - FLOW
    - COMPARISON
    - REPORT
    - GENERAL

    Return ONLY the chosen type.
    """,
    expected_output="One intent type",
    agent=structuring_agent
)

writing_task = Task(
    description="""
    Generate the FINAL output.

    Intent: {intent}

    RULES (MANDATORY):
    - If intent == CODE → output ONLY code (no explanation, no markdown)
    - If intent == FLOW → output ONLY step-by-step arrows
    - If intent == COMPARISON → output ONLY a table
    - If intent == REPORT → structured report
    - If intent == GENERAL → concise answer

    DO NOT include multiple formats.
    DO NOT add explanations unless intent == REPORT.
    """,
    expected_output="Final answer for the user",
    agent=writing_agent
)



