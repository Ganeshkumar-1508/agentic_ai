from crew import crew
from langfuse import get_client, propagate_attributes
from dotenv import load_dotenv
from openinference.instrumentation.crewai import CrewAIInstrumentor

load_dotenv()
langfuse = get_client()
CrewAIInstrumentor().instrument(skip_dep_check=True)


if langfuse.auth_check():
    print("Langfuse client is authenticated and ready!")
else:
    print("Authentication failed. Please check your credentials and host.")

def main():
    print("=== CrewAI Report Generator (NVIDIA Cloud) ===")
    topic = input("Enter report topic: ")

    langfuse.score_current_span(
        name="Correct report generated",
        value=0.9,
        comment="User provided a valid topic for report generation.",
        data_type="NUMERIC"
    )

    result = crew.kickoff(inputs={"topic": topic})

    langfuse.score_current_trace(
        name="Report Quality",
        value=1,
        comment="The generated report met the quality expectations.",
        data_type="NUMERIC"
    )

    print("\nFINAL REPORT\n")
    print(result)

    span.update_trace(input=topic, output=result)

if __name__ == "__main__":
    with langfuse.start_as_current_observation(as_type="span", name="CrewAI Report Generation") as span:
        with propagate_attributes(user_id="user_1234", session_id="session_Test"):
            main()
    langfuse.flush()
