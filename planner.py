import json
from crewai.llm import LLM
import os

# 🔥 Use SAME NVIDIA LLM as Crew
planner_llm = LLM(
    provider="nvidia",
    model=os.getenv("LITELLM_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL"),
)

PLANNER_PROMPT = """
You are a strict execution planner for an AI system.

Your job is to decide what agents must run.

Available agents:
- TEXT
- IMAGE

CRITICAL RULES:

1. If the user explicitly requests to generate, draw, create, or produce an image,
   you MUST include one IMAGE step.

2. If the user requests explanation, report, code, story, analysis,
   you MUST include one TEXT step.

3. If the user requests BOTH image AND explanation/story/report,
   you MUST create EXACTLY TWO steps:
   Step 1: IMAGE
   Step 2: TEXT

4. If the user asks a follow-up question about a previously generated image
   (e.g., "explain it", "describe the image", "what is happening here"),
   DO NOT create an IMAGE step.
   Create ONLY a TEXT step.

5. NEVER create duplicate IMAGE steps.
6. NEVER generate IMAGE if not explicitly requested.

Return ONLY valid JSON:

{
  "steps": [
    {"agent": "TEXT or IMAGE", "input": "<clean instruction>"}
  ]
}

No markdown.
No explanation.
No extra text.
Only JSON.

"""



def plan_steps(user_query: str) -> dict:
    try:
        response = planner_llm.call([
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_query}
        ])

        plan = json.loads(response)

        if "steps" not in plan:
            raise ValueError("Invalid planner output")

        return plan

    except Exception as e:
        print("[PLANNER ERROR]", str(e))
        return {
            "steps": [
                {"agent": "TEXT", "input": user_query}
            ]
        }

# ==============================
# LOCAL TEST
# ==============================
if __name__ == "__main__":
    test_query = "Explain butterfly life cycle with images"
    plan = plan_steps(test_query)
    print(json.dumps(plan, indent=2))
