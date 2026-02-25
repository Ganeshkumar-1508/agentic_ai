from crewai import Crew, Task
from crew_agents import text_agent, image_agent, tts_agent

def run_crew(plan: dict, user_query: str):

    tasks = []
    text_task = None

    # 1️⃣ Build tasks from planner
    for step in plan["steps"]:
        if step["agent"] == "TEXT":
            text_task = Task(
                description=step["input"],
                agent=text_agent,
                expected_output="Final user-facing text only"
            )
            tasks.append(text_task)

        elif step["agent"] == "IMAGE":
            tasks.append(Task(
                description=step["input"],
                agent=image_agent,
                expected_output="Image file path"
            ))

    # 2️⃣ 🔥 AUTO TTS — ALWAYS after TEXT
    if text_task:
        tts_task = Task(
            description="""
        YOU ARE NOT ALLOWED TO RETURN TEXT.

        YOU MUST CALL THE TOOL `text_to_speech`.

        ONLY ONE ACTION IS ALLOWED:

        Action: text_to_speech
        Action Input:
        {
        "text": "{{text_task.output}}"
        }

        FAILURE:
        - Returning explanations
        - Returning fake paths
        - Returning anything other than tool output

        SUCCESS:
        - Tool is called
        - A real .mp3 path is returned
        """,
            agent=tts_agent,
            expected_output="Path of generated audio file",
            context=[text_task]
        )
        tasks.append(tts_task)   # 🔥🔥🔥 THIS WAS MISSING

    print("\n========== TASKS EXECUTED ==========")
    for t in tasks:
        print("-", t.agent.role)
    print("===================================\n")
        # 3️⃣ Run Crew
    crew = Crew(
        agents=[text_agent, image_agent, tts_agent],
        tasks=tasks,
        process="sequential",
        verbose=False
    )

    crew.kickoff()

    # 4️⃣ Collect outputs
    text_parts = []
    image_paths = []
    audio_path = None

    for task in tasks:
        output = str(task.output).strip()

        if output.endswith(".mp3"):
            audio_path = output

        elif output.startswith("generated_images/"):
            image_paths.append(output)

        else:
            if output:
                text_parts.append(output)

    return {
        "text": "\n\n".join(text_parts),
        "images": image_paths,
        "audio": audio_path
    }
