# core.py
import os
import re
import difflib
import threading
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

# --- 1. Query Preprocessing ---
def preprocess_query(query: str) -> str:
    query = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', query)
    query = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', query)
    injection_phrases = ["ignore previous instructions", "ignore all instructions", "system prompt"]
    query_lower = query.lower()
    for phrase in injection_phrases:
        if phrase in query_lower: return "Invalid query detected."
    return query.strip()

# --- 2. Semantic & Fuzzy Matching ---
def get_domain_synonyms() -> Dict[str, List[str]]:
    return {
        "pay": ["salary", "income", "earnings", "wage", "compensation"],
        "job": ["role", "designation", "position", "title", "job_title"],
        "employee": ["employee_id", "emp_id", "staff_id", "worker"],
        "applicant": ["applicant_id", "customer_id", "user_id"],
        "details": ["info", "information", "data"],
        "list": ["show", "display"],
        "revenue": ["sales", "turnover", "income", "top_line", "total_sales"],
        "profit": ["net_income", "bottom_line", "earnings", "margin"],
        "amount": ["value", "principal", "balance", "sum", "total"],
        "default": ["npa", "non_performing", "delinquency", "failure"],
        "risk": ["risk_score", "credit_risk", "probability_of_default"]
    }

def get_fuzzy_column_matches(query_tokens: List[str], df_columns: List[str]) -> List[str]:
    matched_cols = []
    for token in query_tokens:
        matches = difflib.get_close_matches(token, df_columns, n=1, cutoff=0.75)
        if matches: matched_cols.append(matches[0])
        synonyms = get_domain_synonyms()
        if token in synonyms:
            for syn in synonyms[token]:
                if syn in df_columns: matched_cols.append(syn)
    return list(set(matched_cols))

# --- 3. Schema Analysis ---
def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    metadata = {"columns": {}, "primary_key": None, "row_count": len(df)}
    potential_pks = []
    for col in df.columns:
        col_data = df[col]
        col_type = str(col_data.dtype)
        is_numeric = pd.api.types.is_numeric_dtype(col_data)
        semantic_type = "text"
        
        if is_numeric:
            if col_data.between(0, 100).all() and col_data.mean() < 30: semantic_type = "percentage"
            elif col_data.abs().mean() > 100: semantic_type = "currency"
            else: semantic_type = "numeric"
        else:
            non_null_data = col_data.dropna().astype(str)
            if len(non_null_data) > 0:
                if non_null_data.str.match(r'^\d{4}-\d{2}-\d{2}').all(): semantic_type = "datetime_string"
                elif non_null_data.str.match(r'^[\$\€\£]?\s?[\d,]+\.?\d*$').all(): semantic_type = "currency_string"
        
        metadata["columns"][col] = {"type": col_type, "semantic_type": semantic_type, "is_numeric": is_numeric, "unique_count": col_data.nunique()}
        if col_data.nunique() == len(df) and not col_data.isnull().any(): potential_pks.append(col)
        
    if potential_pks:
        for pk in potential_pks:
            if 'id' in pk.lower(): metadata["primary_key"] = pk; break
        if not metadata["primary_key"]: metadata["primary_key"] = potential_pks[0]
    return metadata

def generate_schema_description(filename: str, df: pd.DataFrame, metadata: Dict) -> str:
    col_details = [f"{col}({meta.get('semantic_type', 'text')})" for col, meta in metadata['columns'].items()]
    return f"Dataset: {filename}\nTotal Records: {len(df)}\nPrimary Key: {metadata.get('primary_key', 'unknown')}\nColumns: {', '.join(col_details)}".strip()

# --- 4. Validation ---
def validate_pandas_code(code_str: str, df_columns: List[str], schema: Dict) -> Tuple[bool, str]:
    if not code_str: 
        return False, "Code is empty"
    if "result =" not in code_str: 
        return False, "Code must assign to 'result'"
    
    referenced_cols = re.findall(r"df\[['\"](.*?)['\"]\]", code_str)
    
    for col in referenced_cols:
        if col not in df_columns: 
            return False, f"Column '{col}' does not exist"
        
        col_meta = schema['columns'].get(col, {})
        is_numeric = col_meta.get('is_numeric', False)
        
        if is_numeric:
            str_patterns = [
                rf"df\[['\"]{re.escape(col)}['\"]\]\.str\.",
                rf"df\[['\"]{re.escape(col)}['\"]\]\s*\.str\s*\.",
            ]
            for pattern in str_patterns:
                if re.search(pattern, code_str):
                    return False, f"Column '{col}' is numeric. Remove .str accessor!"
    
    forbidden_patterns = [
        (r'\bimport\s+', "Imports not allowed"),
        (r'\bos\.', "os module not allowed"),
        (r'\bsys\.', "sys module not allowed"),
        (r'\bsubprocess', "subprocess not allowed"),
        (r'\beval\s*\(', "eval not allowed"),
        (r'\bexec\s*\(', "exec not allowed"),
        (r'\bopen\s*\(', "open() not allowed"),
    ]
    
    for pattern, msg in forbidden_patterns:
        if re.search(pattern, code_str):
            return False, msg
    
    return True, "Valid"

# --- 5. Safe Execution ---
def safe_execute_pandas(code_str: str, df: pd.DataFrame) -> Tuple[Any, Optional[str]]:
    result = [None, None]  # [result_data, error_message]
    
    def target():
        try:
            exec_globals = {
                'pd': pd,
                'np': np,
                'df': df.copy(), 
                'result': None,
                '__builtins__': {
                    'print': print,  # <-- ADDED THIS: LLMs love adding print() statements
                    'len': len, 'range': range, 'int': int, 'float': float,
                    'str': str, 'bool': bool, 'list': list, 'dict': dict,
                    'tuple': tuple, 'set': set, 'abs': abs, 'min': min,
                    'max': max, 'sum': sum, 'round': round, 'isinstance': isinstance,
                    'type': type, 'enumerate': enumerate, 'zip': zip, 'map': map,
                    'filter': filter, 'sorted': sorted, 'any': any, 'all': all,
                    'None': None, 'True': True, 'False': False,
                    'ValueError': ValueError, 'TypeError': TypeError, 'KeyError': KeyError,
                }
            }
            exec(code_str, exec_globals)
            result[0] = exec_globals.get('result')
        except Exception as e:
            result[1] = str(e)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=5.0)

    if thread.is_alive():
        return None, "Execution timed out."
    return result[0], result[1]

# --- 6. Prompts ---
def get_pandas_prompt(query: str, schema: Dict, df_head: str, error_feedback: str = None) -> str:
    col_instructions = []
    for col, meta in schema['columns'].items():
        dtype = meta.get('type', 'unknown')
        semantic = meta.get('semantic_type', 'text')
        is_numeric = meta.get('is_numeric', False)
        
        if is_numeric:
            col_instructions.append(f"- '{col}': NUMERIC (dtype: {dtype}). DO NOT use .str accessor on this!")
        elif semantic == "currency_string":
            col_instructions.append(f"- '{col}': TEXT with currency (dtype: {dtype}). Convert: .str.replace('$','').str.replace(',','').astype(float)")
        elif semantic == "datetime_string":
            col_instructions.append(f"- '{col}': TEXT with date (dtype: {dtype}). Convert: pd.to_datetime()")
        else:
            col_instructions.append(f"- '{col}': TEXT (dtype: {dtype})")
    
    pk = schema.get('primary_key', 'None')
    query_lower = query.lower()
    
    # --- ULTIMATE SMART QUERY DETECTION ---
    
    # 1. TOTAL COUNT
    needs_total_count = bool(re.search(r"how many\s+\w+\s+(are there|in the|does the|in this|contains)", query_lower)) or \
                        any(kw in query_lower for kw in ["total records", "total rows", "number of rows", "how many rows"])
    
    # 2. FILTERED COUNT
    is_filtered_count = bool(re.search(r"\b(how many|count of|number of)\b", query_lower)) and not needs_total_count
    
    # 3. WHO/WHICH MAX/MIN (e.g., "Who is the highest paid", "Which applicant has the lowest score")
    is_who_which = bool(re.search(r"\b(who|which)\b", query_lower)) and \
                   bool(re.search(r"\b(highest|maximum|lowest|minimum|most|least|top|best|worst)\b", query_lower))
    
    # 4. MATH/AGGREGATION
    is_aggregation = any(kw in query_lower for kw in ["average", "mean", "total of", "sum of", "maximum", "highest", "lowest", "minimum", "group by"]) and not is_who_which
    
    # 5. FULL DETAILS
    needs_all_cols = any(kw in query_lower for kw in ["details", "all info", "entire row", "full details", "profile"])
    
    # --- ASSIGN EXACT INSTRUCTION ---
    if needs_total_count:
        column_rule = "The user wants the TOTAL count of ALL rows. DO NOT filter. Use EXACTLY: result = len(df)"
    elif is_filtered_count:
        column_rule = "The user wants a COUNT. Wrap your filter in len(). Example: result = len(df[df['col'] > value])"
    elif is_who_which:
        # NEW FIX: "Who" queries need the person's details, not just the max number
        column_rule = "The user wants to know WHICH person/row has the max/min value. Use idxmax()/idxmin() to get the row. Example: result = df.loc[df['col'].idxmax()].to_dict()"
    elif is_aggregation:
        column_rule = "The user wants a math calculation. Apply .mean(), .sum(), .max(), or .min() to the specific column. Example: result = df['col'].mean()"
    elif needs_all_cols:
        column_rule = "The user asked for DETAILS. Return ALL columns. Use EXACTLY: result = df[df['id'] == val].to_dict(orient='records')"
    else:
        column_rule = "Return ONLY the 1-2 specific columns requested: result = df[df['id'] == val][['col1', 'col2']]"
    
    error_section = ""
    if error_feedback:
        error_section = f"**CRITICAL ERROR:** {error_feedback}"
    
    return f"""You are a Python Data Analyst. The variable 'df' ALREADY EXISTS. Write code to answer the query.

**SCHEMA:**
Primary Key: {pk}
Columns:
{chr(10).join(col_instructions)}

**SAMPLE DATA:**
{df_head}

**RULES:**
1. 'df' ALREADY EXISTS. DO NOT use pd.DataFrame().
2. Assign output to 'result'.
3. {column_rule}
4. NO imports.
{error_section}
QUERY: "{query}"
PYTHON CODE:"""


def get_natural_language_prompt(query: str, data_context: str) -> str:
    return f"""You are a Data Interpreter. Read the Database Output and answer the User Question.

RULE 1: The Database Output IS the exact answer. You MUST use it.
RULE 2: If the output is a single number (e.g., "275" or "54300.5"), directly answer using that exact number. Add commas to numbers over 999. If the question implies money, add currency symbols.
RULE 3: If the output is a list of dictionaries `[{{...}}]`, format it into a readable summary or bullet points.
RULE 4: Map Yes/No to business terms (e.g., Approved/Declined).
RULE 5: ONLY say "No relevant data found" if the output literally says "execution_failed" or is completely empty.

USER QUESTION: {query}
DATABASE OUTPUT: {data_context}
ANSWER:"""

def extract_code(raw: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", raw, re.DOTALL)
    code = match.group(1).strip() if match else raw.strip()
    
    # Automatically clean up stubborn LLM boilerplate to prevent validation errors
    cleaned_lines = []
    for line in code.splitlines():
        stripped = line.strip()
        
        # Skip import statements (pd and np are already injected into exec)
        if stripped.startswith("import ") or stripped.startswith("from "): 
            continue
            
        # Skip LLM attempts to recreate the dataframe from scratch
        if stripped.startswith("df = pd.DataFrame(") or stripped.startswith("result = pd.DataFrame("): 
            continue
            
        # Skip weird retry comments LLMs leave behind
        if "Removed import" in stripped or "# Define the DataFrame" in stripped: 
            continue
            
        cleaned_lines.append(line)
        
    final_code = "\n".join(cleaned_lines).strip()
    
    # Fallback: if our cleaning accidentally removed the result= line, find it in raw text
    if "result =" not in final_code:
        for line in raw.splitlines():
            if "result =" in line: return line.strip()
            
    return final_code