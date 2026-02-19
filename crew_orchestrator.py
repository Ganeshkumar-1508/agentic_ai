from crewai import Crew, Task
from crew_agents import text_agent, image_agent

def run_crew(plan: dict, user_query: str):

    tasks = []

    for step in plan["steps"]:
        if step["agent"] == "TEXT":
            tasks.append(Task(
                description=step["input"],
                agent=text_agent,
                expected_output="Text response"
            ))

        elif step["agent"] == "IMAGE":
            tasks.append(Task(
                description=step["input"],
                agent=image_agent,
                expected_output="Image file path"
            ))

    crew = Crew(
        agents=[text_agent, image_agent],
        tasks=tasks,
        process="sequential",
        verbose=False
    )

    # Run crew
    crew.kickoff()

    # -----------------------------------
    # ✅ COLLECT OUTPUTS FROM TASKS
    # -----------------------------------
    text_parts = []
    image_paths = []

    for task in tasks:
        output = str(task.output).strip()

        if output.startswith("generated_images/") and output.endswith(".png"):
            image_paths.append(output)
        else:
            if output:
                text_parts.append(output)

    return {
        "text": "\n\n".join(text_parts),
        "images": image_paths
    }
