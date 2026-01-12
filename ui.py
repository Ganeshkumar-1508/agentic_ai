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
