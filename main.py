from crew import crew
import time

def detect_intent(text: str) -> str:
    t = text.lower()

    if any(k in t for k in ["code", "program", "function", "implementation"]):
        return "CODE"
    if any(k in t for k in ["flow", "diagram", "workflow", "steps"]):
        return "FLOW"
    if any(k in t for k in ["compare", "comparison", "difference"]):
        return "COMPARISON"
    if any(k in t for k in ["report", "explain", "analysis"]):
        return "REPORT"

    return "GENERAL"

def main():
    print("=== CrewAI Smart Intent-Based Generator ===")

    while True:
        user_input = input("\nEnter your question (or 'q' / 'quit'): ").strip()

        if user_input.lower() in ("q", "quit"):
            print("Exiting. Goodbye!")
            break

        intent = detect_intent(user_input)
        print(f"[Detected Intent → {intent}]")

        start = time.time()

        result = crew.kickoff(
            inputs={
                "topic": user_input,
                "intent": intent
            }
        )

        print("\nFINAL OUTPUT\n")
        print(result)

        print(f"\nExecution time: {time.time() - start:.2f} seconds")

if __name__ == "__main__":
    main()