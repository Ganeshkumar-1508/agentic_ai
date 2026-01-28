from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import os
import uvicorn
from io import BytesIO
from crew import crew
from cache.cache_manager import get_from_cache, store_in_cache, delete_from_cache

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    document_context: str | None = None


class DocumentRequest(BaseModel):
    format: str = "txt"  # txt, pdf, docx


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== GENERATE REPORT FUNCTION ====================
def generate_report(topic: str):
    """
    Generate a report for the given topic using cached data if available.
    
    This function:
    1. Checks if the answer exists in cache
    2. If found in cache, returns cached answer immediately
    3. If not found, fetches fresh data from web using CrewAI
    4. Stores the new answer in cache for future use
    """
    # Check cache first
    cached_answer = get_from_cache(topic)
    
    if cached_answer:
        return {"output": cached_answer, "from_cache": True}
    
    # If cache miss, fetch from web
    result = crew.kickoff(inputs={"topic": topic})
    
    # Store in cache for future use
    result_str = str(result.raw if hasattr(result, 'raw') else result)
    store_in_cache(topic, result_str)
    
    return {"output": result_str, "from_cache": False}

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
    try:
        topic = req.query
        
        # Generate report using cache-first approach
        result = generate_report(topic)
        
        return {
            "result": result["output"],
            "from_cache": result["from_cache"],
            "source": None
        }
    except Exception as e:
        return {
            "result": f"Error: {str(e)}",
            "from_cache": False,
            "source": None,
            "error": True
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
