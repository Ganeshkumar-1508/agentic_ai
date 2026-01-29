
from crewai import Crew
from tasks import research_task, analysis_task, structuring_task, writing_task,code_task,code_research_task  

crew = Crew(
    # verbose=False,
    # tracing=False,
    # agents=[
    #     research_task.agent,
    #     analysis_task.agent,
    #     structuring_task.agent,
    #     writing_task.agent
    # ],
    tasks=[
        research_task,
        analysis_task,
        structuring_task,
        writing_task
    ],
    verbose=True
)
code_crew = Crew(
    tasks=[code_task],
    verbose=False
)

# ===================== EXTENSION: WEB-ASSISTED CODE CREW =====================

code_web_crew = Crew(
    tasks=[
        code_research_task,  # web search (context only)
        code_task            # final code generation
    ],
    verbose=False
)

