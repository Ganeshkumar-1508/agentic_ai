import crew_config
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import uuid

from planner import plan_steps
# from text_agent import generate_text
# from image_agent import generate_image
# from llm_config import client, MODEL_NAME
from crew_orchestrator import run_crew



# ==============================
# IMAGE JOB STORE
# ==============================
image_jobs = {}  # job_id -> image_path | None


# ==============================
# IMAGE INTENT CHECK (DYNAMIC, LLM-BASED)
# ==============================
# def user_explicitly_requested_image(query: str) -> bool:
#     """
#     Returns True ONLY if the user explicitly asks for an image / diagram / visual.
#     Fully dynamic, no keywords, no hardcoding.
#     """
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "Answer with ONLY true or false.\n\n"
#                 "true  → user explicitly asks for an image, diagram, drawing, or visual\n"
#                 "false → report, explanation, essay, code, summary without images"
#             )
#         },
#         {
#             "role": "user",
#             "content": query
#         }
#     ]

#     response = client.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.0
#     )

#     return response.choices[0].message.content.strip().lower() == "true"


# # ==============================
# # BACKGROUND IMAGE JOB
# # ==============================
# def run_image_job(job_id: str, prompt: str):
#     result = generate_image(prompt)

#     if result and result.get("image_path"):
#         image_jobs[job_id] = result["image_path"]
#     else:
#         image_jobs[job_id] = None


# ==============================
# FASTAPI APP
# ==============================
app = FastAPI()


# ==============================
# REQUEST MODEL
# ==============================
class QueryRequest(BaseModel):
    query: str
    context: str | None = None
    image_context: dict | None = None


# ==============================
# MAIN ORCHESTRATOR
# ==============================
@app.post("/process-query")
async def process_query(req: QueryRequest, background_tasks: BackgroundTasks):
    user_query = req.query
    context = req.context
    image_context = req.image_context


    plan = plan_steps(user_query)
    print("PLAN:", plan)


    # image_job_ids = []
    # for img in image_results:
    #     if img and img.get("image_path"):
    #         job_id = str(uuid.uuid4())
    #         image_jobs[job_id] = img["image_path"]
    #         image_job_ids.append(job_id)

    # return {
    #     "text": "\n\n".join(text_outputs) if text_outputs else "⚠️ No text generated.",
    #     "images": image_job_ids,
    #     "plan": plan
    # }
    crew_result = run_crew(plan)

    return {
        "text": crew_result.get("text", ""),
        "images": crew_result.get("images", []),
        "plan": plan
    }


# ==============================
# IMAGE STATUS ENDPOINT
# ==============================
# @app.get("/image-status/{job_id}")
# def image_status(job_id: str):
#     if job_id not in image_jobs:
#         return {"status": "processing"}

#     if image_jobs[job_id] is None:
#         return {"status": "failed"}

#     return {
#         "status": "done",
#         "image_path": image_jobs[job_id]
#     }


# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
