def detect_intent(user_input: str) -> str:
    text = user_input.lower()

    # Keywords that indicate CODE generation
    code_keywords = [
        # explicit coding words
        "code", "program", "script", "function", "algorithm", "implementation",

        # action verbs (CRITICAL FIX)
        "build", "create", "implement", "develop", "design",

        # system / concurrency terms
        "concurrent", "parallel", "multithread", "thread", "executor",

        # language / platform hints
        "virtual threads", "async", "await", "goroutine",

        # configuration / setup / framework related
        "configuration", "config", "setup",
        "security", "authentication", "authorization",
        "api", "endpoint", "service",
        "jdbc", "spring boot", "spring security",
        "fastapi", "flask", "django",
        "driver", "sdk", "framework"
    ]

    # Keywords that indicate REPORT generation
    report_keywords = [
        "report", "essay", "article", "write a report",
        "documentation", "overview"
    ]

    # Keywords that indicate EXPLANATION
    explanation_keywords = [
        "explain", "what is", "how does", "why",
        "difference between", "advantages", "disadvantages"
    ]

    # Intent detection priority
    if any(k in text for k in code_keywords):
        return "CODE"
    elif any(k in text for k in report_keywords):
        return "REPORT"
    elif any(k in text for k in explanation_keywords):
        return "EXPLANATION"
    else:
        return "GENERAL"
