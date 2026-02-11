from crewai import Task
from llm_config import research_agent, analysis_agent, structuring_agent,writing_agent,code_agent, code_research_agent 
   



    
# ===================== REPORT PIPELINE TASKS =====================

research_task = Task(
    description="Search the web for {topic}. Return key facts and source links.",
    expected_output="Facts with sources",
    agent=research_agent
)

analysis_task = Task(
    description="Analyze the research and extract 5 key insights.",
    expected_output="Bullet list of insights",
    agent=analysis_agent
)

structuring_task = Task(
    description="Create a professional report outline from the insights.",
    expected_output="Structured headings",
    agent=structuring_agent
)

writing_task = Task(
    description="Write a short professional report based on the structure.",
    expected_output="Final report",
    agent=writing_agent
)

# ===================== CODE PIPELINE TASKS =====================

#  CODE RESEARCH (WEB)
code_research_task = Task(
    description=(
        "Search official documentation or trusted sources for:\n"
        "{user_request}\n\n"
        "Return a concise technical summary for internal use only.\n"
        "DO NOT include code."
    ),
    expected_output="Technical summary (no code)",
    agent=code_research_agent,
    output_key="code_research_summary" 
)

code_task = Task(
    description=(
        "You are a code generator.\n\n"
        "Your task is to generate correct, executable source code.\n\n"
        "Rules:\n"
        "- Output ONLY valid executable source code\n"
        "- Do NOT include explanations, thoughts, or comments outside the code\n"
        "- Infer the programming language from the user request\n\n"
        "User request:\n"
        "{user_request}\n\n"
        "The output MUST start directly with valid source code."
    ),
    expected_output="Executable source code only",
    agent=code_agent
)





