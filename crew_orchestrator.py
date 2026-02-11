from crewai import Crew, Task
from crew_agents import text_agent

def run_crew(plan: dict):
    tasks = []

    for step in plan["steps"]:
        tasks.append(
            Task(
                description=step["input"],
                agent=text_agent,
                expected_output="High-quality text output"
            )
        )

    crew = Crew(
        agents=[text_agent],
        tasks=tasks,
        process="sequential",
        verbose=False
    )

    return crew.kickoff()
