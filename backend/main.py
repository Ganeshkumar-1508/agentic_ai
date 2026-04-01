# ================== FINAL STABLE HYBRID SYSTEM ==================

import os
import re
import pandas as pd
import pdfplumber
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core import (
    analyze_dataframe, generate_schema_description,
    validate_pandas_code, safe_execute_pandas,
    get_pandas_prompt, get_natural_language_prompt,
    preprocess_query, get_fuzzy_column_matches,
    extract_code
)

# ---------------- CONFIG ----------------
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
VECTOR_STORE_DIR = os.path.join(BASE_DIR, '..', 'vector_store')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

app = FastAPI()
structured_data_store = {}

# ---------------- VECTOR ----------------
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

doc_vector_store = Chroma(
    persist_directory=os.path.join(VECTOR_STORE_DIR, 'docs'),
    embedding_function=embeddings
)

schema_vector_store = Chroma(
    persist_directory=os.path.join(VECTOR_STORE_DIR, 'schemas'),
    embedding_function=embeddings
)

# ---------------- LLM ----------------
llm = ChatOpenAI(
    model="meta/llama-3.1-8b-instruct",
    openai_api_key=os.getenv("NVIDIA_API_KEY"),
    openai_api_base="https://integrate.api.nvidia.com/v1",
    temperature=0
)

# ---------------- INGESTION ----------------
def process_structured(path, filename):
    df = pd.read_csv(path) if filename.endswith('.csv') else pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    metadata = analyze_dataframe(df)
    structured_data_store[filename] = {"df": df, "metadata": metadata}

    schema_vector_store.add_documents([
        Document(
            page_content=generate_schema_description(filename, df, metadata),
            metadata={"filename": filename}
        )
    ])

    print(f"Loaded structured: {filename}")

def process_unstructured(path, filename):
    text = ""

    if filename.endswith('.pdf'):
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    else:
        text = open(path, encoding="utf-8").read()

    docs = [Document(page_content=text, metadata={"source": filename})]
    splits = RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(docs)

    doc_vector_store.add_documents(splits)
    print(f"Loaded unstructured: {filename}")

# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    print("Loading datasets...")

    for file in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, file)

        if file.endswith(('.csv', '.xlsx')):
            process_structured(path, file)

        elif file.endswith(('.pdf', '.txt')):
            process_unstructured(path, file)

# ---------------- CANDIDATES ----------------
def get_candidates(query: str):
    candidates = []
    tokens = query.lower().split()

    # semantic schema scoring
    schema_hits = schema_vector_store.similarity_search(query, k=3)
    schema_scores = {}
    for i, hit in enumerate(schema_hits):
        fname = hit.metadata["filename"]
        schema_scores[fname] = schema_scores.get(fname, 0) + (3 - i) * 5

    for filename, store in structured_data_store.items():
        df = store["df"]
        metadata = store["metadata"]

        score = schema_scores.get(filename, 0)
        is_pk = False

        nums = re.findall(r"\d+", query)

        for col in df.columns:
            for num in nums:
                if df[col].astype(str).eq(num).any():
                    score += 10
                    if col == metadata.get("primary_key"):
                        is_pk = True
                        score += 30

        matches = get_fuzzy_column_matches(tokens, list(df.columns))
        score += len(matches) * 10

        if score > 0:
            candidates.append({
                "filename": filename,
                "score": score,
                "is_pk": is_pk
            })

    candidates.sort(key=lambda x: (x["is_pk"], x["score"]), reverse=True)
    return candidates

# ---------------- CORE EXECUTION ----------------
def route_and_execute(query: str):

    clean_query = preprocess_query(query)
    print(f"\nQuery: {clean_query}")

    query_lower = clean_query.lower()

    # 🔥 INTENT DETECTION
    is_concept_query = any(phrase in query_lower for phrase in [
        "what is", "explain", "definition", "role", "purpose", "meaning"
    ])

    has_number = bool(re.search(r"\d+", clean_query))

    candidates = get_candidates(clean_query)

    best_score = candidates[0]["score"] if candidates else 0
    has_pk = any(c["is_pk"] for c in candidates)

    # ---------------- FINAL ROUTING ----------------

    if is_concept_query:
        print("Routing → Unstructured (Concept Query)")
        docs = doc_vector_store.similarity_search(clean_query, k=3)

        if not docs:
            return {"type": "none", "context": ""}

        context = "\n".join([d.page_content for d in docs])
        return {"type": "unstructured", "context": context}

    elif has_pk:
        filename = [c["filename"] for c in candidates if c["is_pk"]][0]
        print("Routing → Structured (PK Match)")

    elif has_number and candidates:
        filename = candidates[0]["filename"]
        print("Routing → Structured (ID Query)")

    elif best_score >= 25:
        filename = candidates[0]["filename"]
        print(f"Routing → Structured (Strong Score: {best_score})")

    else:
        print("Routing → Unstructured (Default)")
        docs = doc_vector_store.similarity_search(clean_query, k=3)

        if not docs:
            return {"type": "none", "context": ""}

        context = "\n".join([d.page_content for d in docs])
        return {"type": "unstructured", "context": context}

    # ---------------- STRUCTURED EXECUTION ----------------
    df = structured_data_store[filename]["df"]
    metadata = structured_data_store[filename]["metadata"]

    MAX_RETRIES = 2
    error_feedback = None

    for attempt in range(MAX_RETRIES):

        prompt = get_pandas_prompt(clean_query, metadata, df.head(3).to_string(), error_feedback)
        raw_code = llm.invoke(prompt).content

        code = extract_code(raw_code)

        valid, msg = validate_pandas_code(code, list(df.columns), metadata)
        if not valid:
            error_feedback = msg
            continue

        result, err = safe_execute_pandas(code, df)
        if err:
            error_feedback = err
            continue

        return {
            "type": "structured",
            "context": str(result),
            "dataset_used": filename
        }

    return {
        "type": "error",
        "context": f"Failed after retries: {error_feedback}"
    }

# ---------------- API ----------------
class QueryRequest(BaseModel):
    question: str

@app.post("/query")
def query(req: QueryRequest):

    result = route_and_execute(req.question)

    if not result["context"]:
        return {
            "answer": "No relevant data found.",
            "execution_type": "none",
            "dataset_used": None,
            "generated_context": ""
        }

    answer = llm.invoke(
        get_natural_language_prompt(req.question, result["context"])
    ).content

    return {
        "answer": answer,
        "execution_type": result["type"],
        "dataset_used": result.get("dataset_used"),
        "generated_context": result["context"]
    }

# ---------------- RUN ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload=True)