
from crewai import Crew
from tasks import research_task, analysis_task, structuring_task, writing_task

crew = Crew(
    verbose=True,
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
    ]
)
