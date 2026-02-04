import time
from agents import client, SYSTEM_PROMPT, MODEL_NAME

def main():
    print("=== Single-Agent LLM Application ===")
    print("Type 'quit' to exit.\n")

    # Conversation memory
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Assistant: Goodbye ")
            break

        start = time.time()

        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3
        )

        answer = response.choices[0].message.content.strip()

        print("\nAssistant:\n")
        print(answer)
        print(f"\n⏱ Time: {time.time() - start:.2f}s\n")

        messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
