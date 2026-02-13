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
You are an execution planner.

Available agents:
- TEXT
- DATA

RULES:

1. If user asks for dashboard → DATA
2. If user asks for chart/graph/visualize → DATA
3. If input contains multiple numbers → DATA
4. Otherwise → TEXT

Return JSON:

{
  "steps": [
    { "agent": "TEXT or DATA", "input": "<user request>" }
  ]
}
"""

def plan_steps(user_query: str) -> dict:

    lower_query = user_query.lower()

    # Force DATA routing for dashboards, charts, or numeric input
    if (
        "dashboard" in lower_query
        or "chart" in lower_query
        or any(char.isdigit() for char in lower_query)
    ):
        return {
            "steps": [
                {"agent": "DATA", "input": user_query}
            ]
        }

    # Default fallback
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
