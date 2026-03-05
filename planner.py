import json
from crewai.llm import LLM
import os

# SAME NVIDIA LLM as Crew
planner_llm = LLM(
    provider="nvidia",
    model=os.getenv("LITELLM_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL"),
    stop=["</s>"]
)

PLANNER_PROMPT = """
You are an execution planner.

Available agents:
- TEXT   → text generation, explanation, code, stories, reports
- DATA   → extract numeric data and produce charts/graphs
- IMAGE  → generate a NEW image from scratch via AI
- VISION → analyse an image ALREADY uploaded by the user (do NOT use for generating images)

RULES:

1. If user asks for dashboard → DATA
2. If user asks for chart/graph/visualize → DATA
3. If input contains multiple numbers → DATA
4. Otherwise → TEXT
5. If numeric data exists AND chart requested → use DATA agent ONLY.
   DO NOT use IMAGE agent.
6. If the user requests explanation, report, code, story, analysis,
   you MUST include one TEXT step.
7. If the user requests BOTH image AND explanation/story/report,
   you MUST create EXACTLY TWO steps:
   Step 1: IMAGE
   Step 2: TEXT
8. If the user asks a follow-up question about a previously generated image
   (e.g., "explain it", "describe the image", "what is happening here"),
   DO NOT create an IMAGE step.
   Create ONLY a TEXT step.
9. NEVER create duplicate IMAGE steps.
10. NEVER generate IMAGE if not explicitly requested.
11. VISION is handled automatically BEFORE the planner when the user uploads
    an image — you do NOT need to add VISION steps yourself.

Return JSON:

{
  "steps": [
    { "agent": "TEXT or DATA or IMAGE", "input": "<user request>" }
   ]
}

"""


def plan_steps(user_query: str) -> dict:

    prompt = f"""
{PLANNER_PROMPT}

User request:
{user_query}

Return ONLY valid JSON.
"""

    response = planner_llm.call(prompt)

    try:
        plan = json.loads(response)

        # safety validation
        if "steps" not in plan:
            raise ValueError("Invalid planner output")

        return plan

    except Exception as e:

        # fallback safety
        lower_query = user_query.lower()

        if any(k in lower_query for k in ["image", "draw", "generate", "create", "illustrate"]):
            return {
                "steps": [
                    {"agent": "IMAGE", "input": user_query}
                ]
            }

        elif any(k in lower_query for k in ["chart", "graph", "dashboard"]) or any(char.isdigit() for char in lower_query):
            return {
                "steps": [
                    {"agent": "DATA", "input": user_query},
                    {
                        "agent": "TEXT",
                        "input": f"Explain the insights from the chart generated for: {user_query}"
                    }
                ]
            }

        else:
            return {
                "steps": [
                    {"agent": "TEXT", "input": user_query}
                ]
            }