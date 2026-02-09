import json
from llm_config import client, MODEL_NAME

# ==============================
# PLANNER SYSTEM PROMPT
# ==============================
PLANNER_PROMPT = """
You are an execution planner for an agentic AI system.

Your task is to analyze the user request and decide:
- which agents are required
- the correct execution order

Available agents:
- TEXT  : explanations, reasoning, code, reports, summaries
- IMAGE : ONLY if the user EXPLICITLY asks for an image, diagram, or visual
- GRAPH : ONLY if the user explicitly asks for charts or plots

STRICT RULES:
- Do NOT include IMAGE or GRAPH unless the user clearly asks for it
- Reports, essays, explanations default to TEXT ONLY
- Do NOT add images implicitly

Return ONLY valid JSON.
Do NOT explain anything.
Do NOT add markdown.

Output format:
{
  "steps": [
    { "agent": "<AGENT_NAME>", "input": "<WHAT_THE_AGENT_SHOULD_DO>" }
  ]
}
"""

# ==============================
# PLANNER FUNCTION (SAFE)
# ==============================
def plan_steps(user_query: str) -> dict:
    """
    Uses the LLM to decide which agents are needed
    and in what order.

    ALWAYS returns a valid plan.
    NEVER crashes the pipeline.
    """

    try:
        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_query}
        ]

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0
        )

        plan_text = response.choices[0].message.content.strip()

        # 🔐 HARD JSON PARSE SAFETY
        plan = json.loads(plan_text)

        # 🔐 STRUCTURE SAFETY
        if not isinstance(plan, dict):
            raise ValueError("Planner output is not a dict")

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Planner JSON missing steps array")

        # 🔐 STEP VALIDATION
        valid_agents = {"TEXT", "IMAGE", "GRAPH"}
        cleaned_steps = []

        for step in plan["steps"]:
            agent = step.get("agent")
            input_text = step.get("input")

            if agent not in valid_agents:
                continue

            cleaned_steps.append({
                "agent": agent,
                "input": input_text or user_query
            })

        # 🔐 FINAL FALLBACK
        if not cleaned_steps:
            cleaned_steps = [
                {"agent": "TEXT", "input": user_query}
            ]

        return {"steps": cleaned_steps}

    except Exception as e:
        print("[PLANNER ERROR]", str(e))

        # 🔁 ULTIMATE SAFE FALLBACK
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
