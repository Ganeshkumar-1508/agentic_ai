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
You are an execution planner for an AI system.

Your task is to analyze the user input and create execution steps.

Available agents:
- TEXT : explanations, code, reports, reasoning, or conversational replies

IMPORTANT RULES:

1. If the user input is a simple greeting or small talk
   (like hello, hi, good morning, hey, etc.),
   then create a TEXT step that instructs the agent to
   respond with a short, friendly greeting message only.
   Do NOT generate explanations about greetings.

2. If the user input is a real request (report, explanation, code, etc.),
   then create a TEXT step using the full user request.

Return ONLY valid JSON in this format:

{
  "steps": [
    { "agent": "TEXT", "input": "<what the agent should do>" }
  ]
}
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
