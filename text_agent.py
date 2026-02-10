"""
Text Agent
----------
Responsible for all text-based generation:
- explanations
- code generation
- reports
- summaries
"""

from llm_config import client, MODEL_NAME, SYSTEM_PROMPT


def generate_text(prompt: str, context: str | None = None,image_context: dict | None = None) -> str:
    """
    Safe text generation wrapper.
    ALWAYS returns a string.
    NEVER crashes the pipeline.
    """

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if context:
            messages.append({
                "role": "assistant",
                "content": f"Previous context:\n{context}"
            })
        
        if image_context:
            messages.append({
                "role": "system",
                "content": (
                    "The user previously generated an image with this description:\n"
                    f"{image_context['prompt']}\n\n"
                    "Use this image as context when answering the next question."
                )
            })


        messages.append({
            "role": "user",
            "content": prompt
        })

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3
        )

        # 🔐 HARD SAFETY CHECK
        if (
            not response
            or not response.choices
            or not response.choices[0].message
            or not response.choices[0].message.content
        ):
            return "⚠️ The model did not return a valid response. Please try again."

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("[TEXT_AGENT ERROR]", str(e))
        return "⚠️ An internal error occurred while generating the response."


# ==============================
# Local testing (safe to remove)
# ==============================
if __name__ == "__main__":
    test_prompt = "Write a Java program to reverse a string"
    output = generate_text(test_prompt)

    print("\n=== TEXT AGENT OUTPUT ===\n")
    print(output)
