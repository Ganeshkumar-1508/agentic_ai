import time
from crew import crew, code_web_crew, code_crew
from intent_detector import detect_intent


def needs_web_search(user_input: str) -> bool:
    keywords = [
        "latest",
        "best practices",
        "official",
        "documentation",
        "new",
        "updated"
    ]
    text = user_input.lower()
    return any(k in text for k in keywords)


def clean_code_output(raw_output: str) -> str:
    """
    Cleans LLM output to behave like ChatGPT:
    - Removes markdown fences
    - Removes leading language name (java, python, etc.)
    """
    output = raw_output.replace("```", "").strip()
    lines = output.splitlines()

    if not lines:
        return output

    first_line = lines[0].strip().lower()

    language_names = {
        "java", "python", "javascript", "js",
        "typescript", "ts", "c", "cpp",
        "go", "rust", "kotlin", "scala",
        "php", "ruby"
    }

    if first_line in language_names:
        lines = lines[1:]

    return "\n".join(lines).strip()


def main():
    print("=== CrewAI Smart Intent-Based Generator ===")

    while True:
        user_input = input("\nEnter your question (or 'q' / 'quit'): ").strip()

        if user_input.lower() in ("q", "quit"):
            print("Exiting. Goodbye!")
            break

        intent = detect_intent(user_input)
        start = time.time()

        if intent == "CODE":
            if needs_web_search(user_input):
                result = code_web_crew.kickoff(
                    inputs={
                        "user_request": user_input,
                        "code_research_summary": ""
                    }
                )
            else:
                result = code_crew.kickoff(
                    inputs={
                        "user_request": user_input,
                        "code_research_summary": ""
                    }
                )
        else:
            result = crew.kickoff(
                inputs={"topic": user_input}
            )

        print("\nFINAL OUTPUT\n")

        if intent == "CODE":
            cleaned_output = clean_code_output(str(result))
            print(cleaned_output)
        else:
            print(result)

        print(f"\nExecution time: {time.time() - start:.2f} seconds")


if __name__ == "__main__":
    main()


