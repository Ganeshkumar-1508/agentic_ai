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



# from crew import crew
# from cache.cache_manager import get_from_cache, store_in_cache, delete_from_cache
# from agents import llm
# import time


# # -------- Helpers --------

# def is_code_request(text: str) -> bool:
#     text = text.lower()
#     return any(
#         k in text for k in ["code", "program", "function", "implementation"]
#     )


# def detect_explicit_language(text: str):
#     text = text.lower()

#     if "python" in text:
#         return "Python"
#     if "java" in text:
#         return "Java"
#     if "c++" in text or "cpp" in text:
#         return "C++"
#     if "javascript" in text or "js" in text:
#         return "JavaScript"

#     return None  # not specified


# # -------- Main --------

# def main():
#     print("=== CrewAI Smart Generator (Code + Report + Cache) ===")

#     while True:
#         topic = input("\nEnter your question (or 'q' / 'quit'): ").strip()

#         if topic.lower() in ("q", "quit"):
#             print("Exiting the application. Goodbye..")
#             break

#         start_time = time.time()

#         # ---------------- Cache First ----------------
#         cached_answer = get_from_cache(topic)

#         if cached_answer:
#             print("\nFinal Output (From Cache)\n")
#             print(cached_answer)

#             refresh = input("\nDo you want latest data? (T/F): ").strip().lower()
#             if refresh != "t":
#                 print("\nUsing cached data")
#                 continue

#             # user wants fresh  remove old cache
#             delete_from_cache(topic)

#         # ---------------- Detect Intent ----------------
#         code_request = is_code_request(topic)
#         explicit_language = detect_explicit_language(topic)

#         final_output = ""  # THIS will be cached

#         # ==================================================
#         # CODE MODE
#         # ==================================================
#         if code_request:

#             # Explicit language  single output
#             if explicit_language:
#                 prompt = (
#                     f"Write ONLY {explicit_language} code for the following request:\n\n"
#                     f"{topic}\n\n"
#                     "Rules:\n"
#                     "- Return ONLY code\n"
#                     "- No explanation\n"
#                     "- No headings\n"
#                     "- No extra text"
#                 )

#                 final_output = llm.call(prompt)

#             # Default  multi-language output
#             else:
#                 languages = ["Python", "Java", "C++"]
#                 outputs = []

#                 for lang in languages:
#                     prompt = (
#                         f"Write ONLY {lang} code for the following request:\n\n"
#                         f"{topic}\n\n"
#                         "Rules:\n"
#                         "- Return ONLY code\n"
#                         "- No explanation\n"
#                         "- No headings\n"
#                         "- No extra text"
#                     )

#                     code = llm.call(prompt)
#                     outputs.append(f"--- {lang} Code ---\n{code}")

#                 final_output = "\n\n".join(outputs)

#         # ==================================================
#         # REPORT MODE
#         # ==================================================
#         else:
#             final_output = crew.kickoff(inputs={"topic": topic})

#         # ---------------- Store in Cache ----------------
#         store_in_cache(topic, str(final_output))

#         # ---------------- Print Output ----------------
#         print("\nFinal Output\n")
#         print(final_output)

#         end_time = time.time()
#         print(f"\nExecution time: {end_time - start_time:.2f} seconds")


# if __name__ == "__main__":
#     main()
