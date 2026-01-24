from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import os

from main import generate_report

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    document_context: str | None = None


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------
# document upload (optional)
# ---------------------------
@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "stored", "filename": file.filename}


# ---------------------------
# chat endpoint (MAIN)
# ---------------------------
@app.post("/process-query")
async def process_query(req: QueryRequest):
    topic = req.query

    result = generate_report(topic)

    return {
        "result": result,
        "source": None
    }
