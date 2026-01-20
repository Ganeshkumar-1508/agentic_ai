import streamlit as st
import requests

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Agent Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Agent Assistant")
st.caption("Chat with AI agents using documents or NVIDIA LLM")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "attached_doc" not in st.session_state:
    st.session_state.attached_doc = None

if "doc_processed" not in st.session_state:
    st.session_state.doc_processed = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.divider()

col1, col2 = st.columns([1, 14], gap="small")

with col1:
    with st.popover("➕"):
        uploaded_file = st.file_uploader(
            "",
            type=["pdf", "docx", "txt"],
            label_visibility="collapsed"
        )

        if uploaded_file and not st.session_state.doc_processed:
            with st.spinner("Processing document..."):
                files = {
                    "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
                }

                response = requests.post(
                    f"{FASTAPI_URL}/process-document",
                    files=files
                )

                if response.status_code == 200:
                    st.session_state.attached_doc = uploaded_file.name
                    st.session_state.doc_processed = True

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📎 Document **{uploaded_file.name}** attached successfully."
                    })

                    st.rerun()
                else:
                    st.error("Failed to process document")

with col2:
    prompt = st.chat_input("Ask anything")

if st.session_state.attached_doc:
    st.info(f"📎 Attached: **{st.session_state.attached_doc}**")

# Download section
if st.session_state.messages:
    st.divider()
    st.subheader("📥 Download Generated Document")
    
    col_download1, col_download2, col_download3 = st.columns(3)
    
    with col_download1:
        if st.button("📄 Download as PDF", use_container_width=True):
            with st.spinner("Generating PDF..."):
                payload = {"format": "pdf"}
                response = requests.post(
                    f"{FASTAPI_URL}/generate-document",
                    json=payload
                )
                
                if response.status_code == 200:
                    st.download_button(
                        label="Download PDF",
                        data=response.content,
                        file_name="generated_document.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate PDF")
    
    with col_download2:
        if st.button("📝 Download as DOCX", use_container_width=True):
            with st.spinner("Generating DOCX..."):
                payload = {"format": "docx"}
                response = requests.post(
                    f"{FASTAPI_URL}/generate-document",
                    json=payload
                )
                
                if response.status_code == 200:
                    st.download_button(
                        label="Download DOCX",
                        data=response.content,
                        file_name="generated_document.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate DOCX")
    
    with col_download3:
        if st.button("📋 Download as TXT", use_container_width=True):
            with st.spinner("Generating TXT..."):
                payload = {"format": "txt"}
                response = requests.post(
                    f"{FASTAPI_URL}/generate-document",
                    json=payload
                )
                
                if response.status_code == 200:
                    st.download_button(
                        label="Download TXT",
                        data=response.content,
                        file_name="generated_document.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate TXT")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            payload = {
                "query": prompt,
                "document_context": st.session_state.attached_doc
            }

            response = requests.post(
                f"{FASTAPI_URL}/process-query",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                reply = data.get("result", "")
                source = data.get("source", "")

                if source:
                    reply += f"\n\n*Source: {source}*"

                st.markdown(reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )
            else:
                st.error("Backend error")
