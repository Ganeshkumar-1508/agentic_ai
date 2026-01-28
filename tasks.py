from crewai import Task
from agents import research_agent, analysis_agent, structuring_agent, writing_agent

research_task = Task(
    description="Search the web for {topic}. Find only the most relevant facts and key sources. Keep it brief.",
    expected_output="2-3 key facts with sources",
    agent=research_agent
)

analysis_task = Task(
    description="Extract only the most important insights from the research. Focus on what matters most to answer the question.",
    expected_output="3 key insights (bullet points only)",
    agent=analysis_agent
)

structuring_task = Task(
    description="Create a simple, logical flow to present the answer. Don't use formal report structure - just organize the main points.",
    expected_output="Simple outline with 2-3 main points",
    agent=structuring_agent
)

writing_task = Task(
    description="Write a conversational, clear answer like ChatGPT would - friendly and easy to understand. Keep it concise (2-4 paragraphs max). Only use longer format if the topic truly requires it. Avoid formal report structure.",
    expected_output="Concise, conversational answer (2-4 paragraphs)",
    agent=writing_agent
)

