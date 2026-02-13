from crewai import Crew, Task
from crew_agents import text_agent, data_agent
import pandas as pd
from io import StringIO
import plotly.express as px
import uuid
import os
import re

OUTPUT_DIR = "generated_charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def contains_numeric_data(text: str) -> bool:
    numbers = re.findall(r"\d+\.?\d*", text)
    return len(numbers) >= 2


def render_chart(df, user_query):
    numeric_cols = df.select_dtypes(include='number').columns
    x_col = df.columns[0]
    lower_query = user_query.lower()

    # If user explicitly asks for bar
    if "bar" in lower_query:
        fig = px.bar(df, x=x_col, y=numeric_cols)

    # If explicitly line
    elif "line" in lower_query:
        fig = px.line(df, x=x_col, y=numeric_cols)

    # Auto fallback
    else:
        if len(numeric_cols) == 1:
            fig = px.bar(df, x=x_col, y=numeric_cols[0])
        else:
            fig = px.line(df, x=x_col, y=numeric_cols)

    filename = f"{uuid.uuid4()}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    fig.write_image(path)
    return path


def run_crew(plan: dict):

    text_outputs = []
    images = []

    for step in plan["steps"]:

        # ================= TEXT =================
        if step["agent"] == "TEXT":

            task = Task(
                description=step["input"],
                agent=text_agent,
                expected_output="High-quality text output"
            )

            crew = Crew(
                agents=[text_agent],
                tasks=[task],
                process="sequential",
                verbose=False
            )

            result = crew.kickoff()
            text_outputs.append(str(result))


        # ================= DATA =================
        elif step["agent"] == "DATA":

            task = Task(
                description=(
                    step["input"] +
                    "\n\nExtract structured numeric data.\n"
                    "Return ONLY CSV.\n"
                    "No markdown.\n"
                    "First row must be headers."
                ),
                agent=data_agent,
                expected_output="Raw CSV only"
            )

            crew = Crew(
                agents=[data_agent],
                tasks=[task],
                process="sequential",
                verbose=False
            )

            result = crew.kickoff()
            raw_csv = str(result).strip()

            try:
                df = pd.read_csv(StringIO(raw_csv))
                image_path = render_chart(df, step["input"])
                images.append(image_path)
            except Exception as e:
                text_outputs.append("⚠️ Failed to generate chart from data.")


    return {
        "text": "\n\n".join(text_outputs),
        "images": images
    }

