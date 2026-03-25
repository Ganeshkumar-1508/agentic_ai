import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Dynamic Data AI", layout="wide")

st.title("🤖 Dynamic Data AI System")

# Sidebar
with st.sidebar:
    st.header("📂 File Management")
    uploaded_file = st.file_uploader("Upload Dataset or Document", type=['csv', 'xlsx', 'pdf', 'txt', 'docx'])
    
    if uploaded_file:
        if st.button("Process File"):
            with st.spinner("Processing..."):
                res = requests.post(f"{BACKEND_URL}/upload", files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)})
                if res.status_code == 200:
                    st.success(res.json().get('message'))
                else:
                    st.error(res.json().get('detail', 'Error'))

    if st.button("Refresh System Status"):
        res = requests.get(f"{BACKEND_URL}/health")
        st.json(res.json())

# Main Chat
st.header("💬 Query Interface")

user_query = st.text_input("Ask a question about your data:")

if st.button("Submit"):
    if user_query:
        with st.spinner("Analyzing..."):
            res = requests.post(f"{BACKEND_URL}/query", json={"question": user_query})
            
            if res.status_code == 200:
                data = res.json()
                
                # Metadata
                st.info(f"Execution Type: **{data['execution_type']}**")
                if data['dataset_used']:
                    st.info(f"Dataset Routed: **{data['dataset_used']}**")
                
                # Context
                with st.expander("View Retrieved Context (Evidence)"):
                    st.text(data['generated_context'])
                
                # Answer
                st.subheader("AI Answer")
                st.success(data['answer'])
            else:
                st.error("Backend Error")