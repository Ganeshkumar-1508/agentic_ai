from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import os
import uvicorn

from agents import client, MODEL_NAME, SYSTEM_PROMPT

app = FastAPI()


class QueryRequest(BaseModel):
    query: str


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==============================
# Simple LLM call (NO CREW)
# ==============================
def generate_answer(user_query: str):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
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
@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "stored", "filename": file.filename}


# ==============================
# Main chat endpoint
# ==============================
@app.post("/process-query")
async def process_query(req: QueryRequest):
    try:
        return generate_answer(req.query)
    except Exception as e:
        return {
            "result": f"Error: {str(e)}",
            "error": True
        }


# ==============================
# Run server
# ==============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
