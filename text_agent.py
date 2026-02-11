"""
Text Agent
----------
This file no longer calls any LLM directly.
Crew handles the LLM execution.
"""

def generate_text(prompt: str, context: str | None = None, image_context: dict | None = None) -> str:
    """
    This function is now just a fallback utility.
    Crew will handle real LLM execution.
    """
    return prompt
