from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import os
import uvicorn

from agents import client, MODEL_NAME, SYSTEM_PROMPT

app = FastAPI()


class QueryRequest(BaseModel):
    messages: list



UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==============================
# Simple LLM call (NO CREW)
# ==============================
def generate_answer(messages: list):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.3
    )

    answer = response.choices[0].message.content.strip()

    return {
        "result": answer,
        "from_cache": False,
        "source": None
    }



# ==============================
# Document upload (optional)
# ==============================
@app.post("/process-query")
async def process_query(req: QueryRequest):
    try:
        return generate_answer(req.messages)
    except Exception as e:
        return {
            "result": f"Error: {str(e)}",
            "error": True
        }


# ==============================
# Main chat endpoint
# ==============================
# @app.post("/process-query")
# async def process_query(req: QueryRequest):
#     try:
#         return generate_answer(req.query)
#     except Exception as e:
#         return {
#             "result": f"Error: {str(e)}",
#             "error": True
#         }


# ==============================
# Run server
# ==============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
