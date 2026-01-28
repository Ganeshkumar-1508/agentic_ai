from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import os
import uvicorn
from io import BytesIO

from main import generate_report

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    document_context: str | None = None


class DocumentRequest(BaseModel):
    format: str = "txt"  # txt, pdf, docx


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------
# document upload (optional)
# ---------------------------
@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_file"
    path = os.path.join(UPLOAD_DIR, filename)

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
        "result": result.raw,
        "source": None
    }


# ---------------------------
# document generation endpoint
# ---------------------------
@app.post("/generate-document")
async def generate_document(req: DocumentRequest):
    """
    Generate document in the requested format.
    For now, returns a simple text-based response.
    """
    format_type = req.format.lower()
    
    # Create a simple document content
    content = "Generated Document\n\n" + \
              "This is a placeholder for the generated document.\n" + \
              "To enable full document generation with conversation history, " + \
              "please implement document generation logic.\n"
    
    if format_type == "txt":
        return {
            "data": content,
            "format": "txt",
            "mime": "text/plain"
        }
    elif format_type == "pdf":
        # Placeholder - would need python-pptx or similar
        return {
            "data": content,
            "format": "pdf",
            "mime": "application/pdf"
        }
    elif format_type == "docx":
        # Placeholder - would need python-docx
        return {
            "data": content,
            "format": "docx",
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
    else:
        return {
            "data": content,
            "format": "txt",
            "mime": "text/plain"
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
