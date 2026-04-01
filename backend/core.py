# core.py
import os
import re
import difflib
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins

# --- 1. Query Preprocessing ---

def preprocess_query(query: str) -> str:
    """
    Normalizes natural language queries.
    Example: "applicant1" -> "applicant 1", "emp1005" -> "employee 1005"
    """
    # Add space between letters and numbers
    query = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', query)
    query = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', query)
    return query.strip()

# --- 2. Semantic & Fuzzy Matching Helpers ---

def get_domain_synonyms() -> Dict[str, List[str]]:
    return {
        "pay": ["salary", "income", "earnings", "wage"],
        "earnings": ["salary", "income", "pay"],
        "job": ["role", "designation", "position", "title", "job_title"],
        "role": ["job", "designation", "position", "title", "job_title"], # Added 'role'
        "status": ["loan_status", "approval_status", "state", "active"],
        "score": ["credit_score", "cibil", "rating", "points"],
        "applicant": ["applicant_id", "customer_id", "user_id"],
        "employee": ["employee_id", "emp_id", "staff_id"],
        "details": ["info", "information", "data"],
        "list": ["show", "display"]
    }

def get_fuzzy_column_matches(query_tokens: List[str], df_columns: List[str]) -> List[str]:
    """
    Matches query words to column names using fuzzy logic.
    Handles typos like 'salry' -> 'salary'.
    """
    matched_cols = []
    for token in query_tokens:
        # 1. Fuzzy match (typo handling)
        matches = difflib.get_close_matches(token, df_columns, n=1, cutoff=0.75)
        if matches:
            matched_cols.append(matches[0])
            
        # 2. Synonym match
        synonyms = get_domain_synonyms()
        if token in synonyms:
            for syn in synonyms[token]:
                if syn in df_columns:
                    matched_cols.append(syn)
                    
    return list(set(matched_cols))

# --- 3. Schema Analysis ---

def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    metadata = {
        "columns": {},
        "primary_key": None,
        "row_count": len(df),
    }
    
    potential_pks = []
    
    for col in df.columns:
        col_data = df[col]
        col_type = str(col_data.dtype)
        is_numeric = pd.api.types.is_numeric_dtype(col_data)
        
        metadata["columns"][col] = {
            "type": col_type,
            "is_numeric": is_numeric,
            "unique_count": col_data.nunique()
        }
        
        # PK Detection
        if col_data.nunique() == len(df) and not col_data.isnull().any():
            potential_pks.append(col)
        
    if potential_pks:
        for pk in potential_pks:
            if 'id' in pk.lower():
                metadata["primary_key"] = pk
                break
        if not metadata["primary_key"] and potential_pks:
            metadata["primary_key"] = potential_pks[0]
            
    return metadata

def generate_schema_description(filename: str, df: pd.DataFrame, metadata: Dict) -> str:
    col_details = []
    for col in df.columns:
        col_type = "numeric" if metadata["columns"][col]["is_numeric"] else "categorical"
        col_details.append(f"{col}({col_type})")

    description = f"""
Dataset: {filename}
Total Records: {len(df)}
Primary Key: {metadata.get('primary_key', 'unknown')}
Columns: {', '.join(col_details)}
"""
    return description.strip()

# --- 4. Enhanced Validation ---

def validate_pandas_code(code_str: str, df_columns: List[str], schema: Dict) -> Tuple[bool, str]:
    if not code_str: 
        return False, "Code is empty"
    
    if "result =" not in code_str:
        return False, "Code must assign result to variable 'result'"
        
    referenced_cols = re.findall(r"df\[['\"](.*?)['\"]\]", code_str)
    for col in referenced_cols:
        if col not in df_columns:
            return False, f"Column '{col}' does not exist in dataset"
    
    # Type Safety Check
    for col in referenced_cols:
        if col in schema['columns'] and schema['columns'][col]['is_numeric']:
            if re.search(rf"df\['{col}'\]\.str\.", code_str):
                return False, f"Column '{col}' is numeric. Cannot use .str accessor on it."
            
    forbidden = ['import ', 'os.', 'sys.', 'subprocess', 'eval', 'exec', 'open(']
    if any(f in code_str for f in forbidden):
        return False, "Forbidden operation detected"
        
    return True, "Valid"

# --- 5. Safe Execution with Error Returns ---

def safe_execute_pandas(code_str: str, df: pd.DataFrame) -> Tuple[Any, Optional[str]]:
    """
    Returns: (result, error_message)
    """
    try:
        restricted_globals = {
            '__builtins__': safe_builtins,
            'pd': pd,
            'np': np,
            'df': df,
            'result': None,
            '_getitem_': lambda obj, key: obj[key],
            '_getattr_': getattr,
        }
        
        byte_code = compile_restricted(code_str, filename='<inline>', mode='exec')
        exec(byte_code, restricted_globals, restricted_globals)
        
        result = restricted_globals.get('result')
        return result, None
    except Exception as e:
        return None, str(e)

# --- 6. Robust Pandas Prompt ---

def get_pandas_prompt(query: str, schema: Dict, df_head: str, error_feedback: str = None) -> str:
    col_instructions = []
    for col, meta in schema['columns'].items():
        dtype = "Numeric (int/float)" if meta['is_numeric'] else "String (text)"
        col_instructions.append(f"- '{col}': {dtype}")
    
    cols_text = "\n".join(col_instructions)
    
    error_section = ""
    if error_feedback:
        error_section = f"""
!! CRITICAL ERROR FEEDBACK !!
The previous code you generated failed with this error:
"{error_feedback}"
You MUST fix this error in the new code.
"""

    return f"""
You are an expert Python Data Analyst. Generate a single line of Pandas code to answer the question.

**DATASET SCHEMA:**
{cols_text}

**SAMPLE DATA:**
{df_head}

**STRICT CODING RULES:**
1. Variable is 'df'. Output must be assigned to 'result'.
2. **OUTPUT FORMAT**:
   - **SINGLE VALUE**: If asking for one specific attribute (e.g., 'salary'), return the single value.
   - **DETAILS**: If asking for 'details', 'info', or 'all data' for an ID, return the **entire row as a Pandas Series**.
     - USAGE: `result = df.loc[df['id'] == 1].iloc[0]`
     - **CRITICAL**: Do NOT use `.values[0]` (this strips column names). Use `.iloc[0]` to keep the Series structure.
3. **TYPE SAFETY**:
   - Numeric columns: Use direct comparison (e.g., df['id'] == 1).
   - String columns: Use .str.lower() or .str.contains() for matching.
4. **NO LOOPS OR IMPORTS**.
5. **CRITICAL**: Output **ONLY** the python code. NO explanation text before or after. NO markdown formatting outside code.

{error_section}

**USER QUESTION:** "{query}"

**CODE:**
"""

def get_natural_language_prompt(query: str, data_context: str) -> str:
    return f"""
You are an intelligent Data Interpreter. 
Your goal is to translate raw database outputs into clear, human-readable answers.

**INSTRUCTIONS:**
1. **Analyze User Intent**:
   - If the user asks for **"details"**, **"info"**, or **"all data"**: You MUST format the output as a **clean list** (using bullet points or key-value pairs). Do NOT summarize into a single sentence.
   - If the user asks for a **specific attribute** (e.g., "salary", "email"): Answer directly in a concise sentence.
   
2. **Formatting Details**:
   - If the Data Context contains multiple lines (key : value pairs), present them clearly.
   - Example for "details":
     - **ID**: 1001
     - **Name**: Rahul Sharma
     - **Department**: Engineering
     ...
     
3. **Infer Meaning**: 
   - Use column names to understand values (e.g., 'yes' in 'loan_approved' means 'Approved').
   - Format numbers nicely (add currency symbols if appropriate).

**Current Task:**
User Question: {query}
Data Context: 
{data_context}

Answer:
"""
def extract_code(raw: str) -> str:
    """
    Extracts python code from LLM response safely.
    """
    import re

    match = re.search(r"```(?:python)?\s*(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()

    lines = raw.splitlines()
    for line in lines:
        if "result =" in line:
            return line.strip()

    return raw.strip()