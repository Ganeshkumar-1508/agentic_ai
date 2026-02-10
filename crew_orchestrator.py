from crewai import Agent, Task, Crew
from text_agent import generate_text
from image_agent import generate_image

# ==============================
# CREW ORCHESTRATOR (SAFE MODE)
# ==============================

def run_crew(plan: dict, user_query: str, context: str | None,image_context: dict | None):
    """
    CrewAI is used ONLY as a task container.
    NO LLM calls.
    Execution is manual.
    """

    text_outputs = []
    image_outputs = []

    for step in plan["steps"]:
        agent_type = step["agent"]
        agent_input = step["input"] or user_query

        # ---- TEXT ----
        if agent_type == "TEXT":
            result = generate_text(agent_input, context,image_context)
            text_outputs.append(result)
            context = result

        # ---- IMAGE ----
        elif agent_type == "IMAGE":
            img = generate_image(agent_input)
            if img:
                image_outputs.append(img)

    return text_outputs, image_outputs
