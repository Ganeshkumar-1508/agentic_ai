from crewai import Task
from agents import research_agent, analysis_agent, structuring_agent, writing_agent

research_task = Task(
    description="Search the web for {topic}. Return key facts and source links.",
    expected_output="Facts with sources",
    agent=research_agent
)

analysis_task = Task(
    description="Analyze the research and extract 5 key insights.",
    expected_output="Bullet list of insights",
    agent=analysis_agent
)

structuring_task = Task(
    description="Create a professional report outline from the insights.",
    expected_output="Structured headings",
    agent=structuring_agent
)

writing_task = Task(
    description="Write a short professional report based on the structure.",
    expected_output="Final report",
    agent=writing_agent
)

