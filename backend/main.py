# main.py
import os
import json
import re
import hashlib
import pandas as pd
import pdfplumber
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Local Modules
from core import (
    analyze_dataframe, generate_schema_description, 
    validate_pandas_code, safe_execute_pandas, 
    get_pandas_prompt, get_natural_language_prompt,
    preprocess_query, get_fuzzy_column_matches
)

# --- Configuration ---
load_dotenv()
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL_NAME = "meta/llama-3.1-8b-instruct"
ROUTING_THRESHOLD = 1.5

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
METADATA_DIR = os.path.join(BASE_DIR, '..', 'metadata')
VECTOR_STORE_DIR = os.path.join(BASE_DIR, '..', 'vector_store')
REGISTRY_PATH = os.path.join(METADATA_DIR, 'registry.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# --- Global State ---
structured_data_store = {}

# Vector Stores
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

doc_vector_store = Chroma(
    persist_directory=os.path.join(VECTOR_STORE_DIR, 'docs'),
    embedding_function=embeddings,
    collection_name="documents"
)

schema_vector_store = Chroma(
    persist_directory=os.path.join(VECTOR_STORE_DIR, 'schemas'),
    embedding_function=embeddings,
    collection_name="dataset_schemas"
)

# LLM
llm = None
api_key = os.getenv("NVIDIA_API_KEY")
if api_key:
    llm = ChatOpenAI(
        model=MODEL_NAME,
        openai_api_key=api_key,
        openai_api_base=NVIDIA_BASE_URL,
        temperature=0
    )

# --- Helpers ---

def load_registry():
    if not os.path.exists(REGISTRY_PATH): return {}
    with open(REGISTRY_PATH, 'r') as f: return json.load(f)

def save_registry(registry):
    with open(REGISTRY_PATH, 'w') as f: json.dump(registry, f, indent=4)

def calculate_file_hash(file_content): return hashlib.sha256(file_content).hexdigest()

# --- Ingestion Logic ---

def process_structured(file_path: str, filename: str):
    try:
        if filename.endswith('.csv'): df = pd.read_csv(file_path)
        else: df = pd.read_excel(file_path)
        
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        metadata = analyze_dataframe(df)
        
        structured_data_store[filename] = {"df": df, "metadata": metadata}
        
        try:
            schema_vector_store.delete(ids=[filename])
        except:
            pass
            
        schema_desc = generate_schema_description(filename, df, metadata)
        schema_vector_store.add_documents([
            Document(page_content=schema_desc, metadata={"filename": filename}, id=filename)
        ])
        
        print(f"Processed {filename} and updated schema index.")
        return f"Processed {filename}."
    except Exception as e:
        raise Exception(f"Error processing structured file: {e}")

def process_unstructured(file_path: str, filename: str):
    try:
        if filename.endswith('.pdf'):
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    tables = page.extract_tables()
                    for table in tables:
                        text += "\n" + str(table)
            docs = [Document(page_content=text, metadata={"source_filename": filename})]
        elif filename.endswith('.docx'):
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
            docs = loader.load()
            
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        splits = splitter.split_documents(docs)
        doc_vector_store.add_documents(splits)
        print(f"Processed {filename} into vector store.")
        return f"Processed {filename}."
    except Exception as e:
        raise Exception(e)

# --- Routing & Execution Logic ---

def get_semantic_similarity(query: str, filename: str) -> float:
    """Helper to get similarity score for a specific file."""
    try:
        res = schema_vector_store.similarity_search_with_score(query, k=1, filter={"filename": filename})
        return res[0][1] if res else 999.0
    except:
        return 999.0

def get_keyword_routed_candidates(query: str) -> List[Dict]:
    """
    Advanced Candidate Selection:
    1. Fuzzy matches column names (handles typos).
    2. Expands synonyms (maps 'pay' to 'salary').
    3. Prioritizes Primary Key matches (resolves dataset conflicts).
    """
    candidates = []
    query_lower = query.lower()
    query_tokens = query_lower.split()
    
    for filename, store in structured_data_store.items():
        df = store['df']
        metadata = store['metadata']
        score = 0
        is_pk_match = False
        
        # 1. ID Matching
        pk = metadata.get('primary_key')
        nums_in_query = re.findall(r'\d+', query_lower)
        
        if nums_in_query:
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        for num in nums_in_query:
                            # Check exact match of stringified number
                            if df[col].astype(str).eq(num).any():
                                score += 5
                                if col == pk:
                                    is_pk_match = True
                                    score += 15 # Big bonus for PK match
                    except:
                        pass

        # 2. Column/Synonym Matching
        matched_cols = get_fuzzy_column_matches(query_tokens, df.columns)
        if matched_cols:
            score += len(matched_cols) * 10

        if score > 0:
            candidates.append({
                "filename": filename,
                "score": score,
                "is_pk_match": is_pk_match
            })

    candidates.sort(key=lambda x: (x['score'], x['is_pk_match']), reverse=True)
    return candidates

def route_and_execute(query: str) -> Dict:
    # 1. PREPROCESS
    clean_query = preprocess_query(query)
    print(f"--- Normalized Query: '{clean_query}' ---")
    
    exec_context = {
        "type": "none", 
        "result": None, 
        "context_str": "", 
        "dataset_used": None
    }
    
    # 2. HYBRID ROUTING
    
    # Step A: Check Unstructured (PDF/DOCX) relevance first
    # We fetch top 3 to ensure we have enough context if we route here
    unstructured_docs = doc_vector_store.similarity_search_with_score(clean_query, k=3)
    unstructured_score = 999.0
    if unstructured_docs:
        # Chroma returns L2 distance. Lower is better.
        unstructured_score = unstructured_docs[0][1]

    # Step B: Check Structured Candidates
    candidates = get_keyword_routed_candidates(clean_query)
    
    # Decision Logic
    target_filename = None
    is_unstructured_query = False
    
    # 1. STRONG ID MATCH: If query has an ID that exists in a table, FORCE structured.
    # This handles "details of employee 1003" correctly even if PDFs mention "1003".
    has_strong_pk = any(c['is_pk_match'] for c in candidates)
    
    if has_strong_pk:
        target_filename = [c['filename'] for c in candidates if c['is_pk_match']][0]
        print(f"Routing decision: Structured (Primary Key Match)")
        
    # 2. UNSTRUCTURED MATCH: If no strong ID, check if PDFs are a good match.
    # We raised threshold to 1.5. If distance is < 1.5, it's relevant.
    elif unstructured_score < 1.5: 
        is_unstructured_query = True
        print(f"Routing decision: Unstructured (Semantic Match Score: {unstructured_score:.2f})")

    # 3. KEYWORD MATCH: If no ID, no PDF match, but column names matched.
    elif candidates:
        target_filename = candidates[0]['filename']
        print(f"Routing decision: Structured (Keyword Match)")

    # 4. FALLBACK: If nothing else matched, try Schema Vector Search
    else:
        print("No symbolic matches. Trying Vector Routing...")
        results = schema_vector_store.similarity_search_with_score(clean_query, k=1)
        if results:
            best_doc, best_score = results[0]
            # Only accept if score is VERY good (< 0.5), otherwise it's likely a hallucination
            if best_score < 0.5:
                target_filename = best_doc.metadata['filename']
            else:
                # If schema match is weak, assume it's a general question for PDFs
                is_unstructured_query = True
                print("Weak schema match, defaulting to Unstructured.")

    # 3. EXECUTION
    if is_unstructured_query:
        print("Routing to Unstructured Documents (RAG)")
        if unstructured_docs:
            exec_context['type'] = "unstructured"
            exec_context['context_str'] = "\n".join([d.page_content for d, s in unstructured_docs])
        return exec_context

    if target_filename and target_filename in structured_data_store:
        store = structured_data_store[target_filename]
        df = store['df']
        metadata = store['metadata']
        
        max_retries = 3
        error_msg = None
        
        for attempt in range(max_retries):
            print(f"Attempt {attempt+1} for dataset {target_filename}")
            
            prompt = get_pandas_prompt(clean_query, metadata, df.head(3).to_string(), error_msg)
            code_response = llm.invoke(prompt)
            
            # Robust Extraction
            raw_content = code_response.content
            match = re.search(r"```(?:python)?\s*(.*?)\s*```", raw_content, re.DOTALL)
            if match:
                generated_code = match.group(1).strip()
            else:
                generated_code = raw_content.strip()
            
            if generated_code.startswith("Here is the code:") or generated_code.startswith("This code"):
                generated_code = generated_code.split('\n', 1)[1] if '\n' in generated_code else ""

            print(f"Generated Code:\n{generated_code}")
            
            is_valid, val_msg = validate_pandas_code(generated_code, df.columns, metadata)
            
            if not is_valid:
                error_msg = f"Validation Failed: {val_msg}"
                continue
            
            result, exec_err = safe_execute_pandas(generated_code, df)
            
            if exec_err:
                error_msg = f"Execution Error: {exec_err}"
                continue
            
            if result is not None:
                if isinstance(result, (pd.DataFrame, pd.Series)) and result.empty:
                    print("Structured result empty. Falling back to RAG.")
                    break 
                
                exec_context['type'] = "structured"
                exec_context['dataset_used'] = target_filename
                
                if isinstance(result, (pd.DataFrame, pd.Series)):
                    exec_context['context_str'] = result.to_string()
                else:
                    exec_context['context_str'] = f"The result is: {result}"
                
                return exec_context

    # 4. FALLBACK TO UNSTRUCTURED (RAG)
    print("Routing to Unstructured Documents (RAG) - Fallback")
    docs = doc_vector_store.similarity_search(clean_query, k=3)
    if docs:
        exec_context['type'] = "unstructured"
        exec_context['context_str'] = "\n".join([d.page_content for d in docs])
        
    return exec_context

# --- FastAPI App ---

app = FastAPI(title="Dynamic Data AI System")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    execution_type: str
    dataset_used: Optional[str] = None
    generated_context: str

@app.on_event("startup")
def startup():
    print("--- System Startup: Reloading Existing Datasets ---")
    if not os.path.exists(DATA_DIR):
        return

    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(file_path): continue
        file_type = filename.split('.')[-1].lower()
        if file_type in ['csv', 'xlsx']:
            try:
                process_structured(file_path, filename)
            except Exception as e:
                print(f"Failed to reload {filename}: {e}")
    print("--- Startup Complete ---")

@app.get("/health")
def health():
    return {"status": "online", "datasets": list(structured_data_store.keys())}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    file_hash = calculate_file_hash(contents)
    registry = load_registry()
    
    if file_hash in registry:
        return {"status": "skipped", "message": "Duplicate file."}
        
    temp_path = os.path.join(DATA_DIR, file.filename)
    with open(temp_path, 'wb') as f:
        f.write(contents)
        
    try:
        if file.filename.endswith(('.csv', '.xlsx')):
            msg = process_structured(temp_path, file.filename)
        else:
            msg = process_unstructured(temp_path, file.filename)
            
        registry[file_hash] = {"filename": file.filename}
        save_registry(registry)
        return {"status": "success", "message": msg}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/query", response_model=QueryResponse)
def query_system(request: QueryRequest):
    if not llm:
        raise HTTPException(503, "LLM not connected.")
        
    exec_data = route_and_execute(request.question)
    
    if not exec_data['context_str'] or exec_data['context_str'] == "Empty Result":
        answer = "The requested data is not found in the dataset."
    else:
        nl_prompt = get_natural_language_prompt(request.question, exec_data['context_str'])
        response = llm.invoke(nl_prompt)
        answer = response.content
        
    return QueryResponse(
        answer=answer,
        execution_type=exec_data['type'],
        dataset_used=exec_data['dataset_used'],
        generated_context=exec_data['context_str']
    )