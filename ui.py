import streamlit as st
import requests
from requests.exceptions import ConnectionError
from fpdf import FPDF
from io import BytesIO
FASTAPI_URL = "http://localhost:8000"


def generate_pdf_from_conversation(messages):
    """Generate PDF from conversation messages"""
    pdf = FPDF()
    pdf.add_page()
    
    
    pdf.set_font("Helvetica", "B", 16)
    
    # Title
    pdf.cell(0, 10, "AI Agent Assistant - Conversation", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Generated Conversation Export", ln=True, align="C")
    pdf.ln(5)
    
    # Add each message
    pdf.set_font("Helvetica", "", 11)
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        
       
        content = content.replace("–", "-")  
        content = content.replace("—", "-")  
        content = content.replace(""", '"')  
        content = content.replace(""", '"')  
        content = content.replace("'", "'")  
        content = content.replace("'", "'") 
        
        # Role header
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 51, 102)  # Dark blue
        pdf.cell(0, 6, f"{role}:", ln=True)
        
        # Message content
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)  # Black
        
        # Multi-line text support with encoding
        try:
            pdf.multi_cell(0, 5, content.encode('latin-1', errors='replace').decode('latin-1'))
        except:
            # If encoding fails, try with a simplified version
            pdf.multi_cell(0, 5, str(content)[:500])  # Limit length as fallback
        
        pdf.ln(3)
        
        # Separator
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return pdf_bytes
# page configuration
st.set_page_config(
    page_title="AI Agent Assistant",
    page_icon="🤖",
    layout="wide"
)
# header
st.title("🤖 Chat with AI Assistant")
st.caption("Chat with AI by giving a Query")

# Check if backend is running
@st.cache_resource
def check_backend_health():
    try:
        response = requests.get(f"{FASTAPI_URL}/docs", timeout=3)
        return True
    except (ConnectionError, requests.exceptions.Timeout):
        return False

backend_available = check_backend_health()

if not backend_available:
    st.error("""
    ⚠️ **Backend Server Not Running**
    
    The FastAPI backend is not available at `http://localhost:8000`.
    
    **To fix this:**
    1. Open a new terminal
    2. Run: `python api.py`
    3. The server will start on http://localhost:8000
    4. Then refresh this page
    """)
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "attached_doc" not in st.session_state:
    st.session_state.attached_doc = None

if "doc_processed" not in st.session_state:
    st.session_state.doc_processed = False

# ==================== CHAT INPUT AREA ====================
#st.divider()
#st.subheader("📝 Chat with AI Assistant")

#col1, col2 = st.columns([1,50], gap="small")
# Document uploader
# with col1:
#     with st.popover("➕"):
#         uploaded_file = st.file_uploader(
#             "",
#             type=["pdf", "docx", "txt"],
#             label_visibility="collapsed"
#         )

#         if uploaded_file and not st.session_state.doc_processed:
#             with st.spinner("Processing document..."):
#                 files = {
#                     "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
#                 }

#                 try:
#                     response = requests.post(
#                         f"{FASTAPI_URL}/process-document",
#                         files=files,
#                         timeout=30
#                     )

#                     if response.status_code == 200:
#                         st.session_state.attached_doc = uploaded_file.name
#                         st.session_state.doc_processed = True

#                         st.session_state.messages.append({
#                             "role": "assistant",
#                             "content": f"📎 Document **{uploaded_file.name}** attached successfully."
#                         })

#                         st.rerun()
#                     else:
#                         st.error("Failed to process document")
#                 except ConnectionError:
#                     st.error("Cannot connect to backend server. Please ensure the API is running.")
#                 except requests.exceptions.Timeout:
#                     st.error("Request timed out. The backend server may be processing slowly.")

#with col2:
#    prompt = st.chat_input("Ask anything")

if st.session_state.attached_doc:
    st.info(f"📎 Attached: **{st.session_state.attached_doc}**")

# ==================== MESSAGES AREA ====================
st.divider()
#st.subheader("💬 Conversation")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])                   

prompt = st.chat_input("Ask anything")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Generating..."):
            payload = {
                "query": prompt,
                #"document_context": st.session_state.attached_doc
            }

            reply = ""
            source = ""

            try:
                response = requests.post(
                    f"{FASTAPI_URL}/process-query",
                    json=payload,
                    timeout=120
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
            except ConnectionError:
                st.error("❌ Cannot connect to backend server. Please ensure the API is running on http://localhost:8000")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The backend server may be processing slowly.")

if st.session_state.messages:
    st.divider()
    st.subheader("📥 Download Conversation")
    
    col_download1, col_download2, col_download3, col_download4 = st.columns(4)
    
    with col_download1:
        pdf_data = generate_pdf_from_conversation(st.session_state.messages)

        st.download_button(
            label="📄 Download as PDF",
            data=pdf_data,
            file_name="conversation.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    
    with col_download2:
        if st.button("📋 Download as TXT", use_container_width=True):
            try:
                # Create conversation text
                conversation_text = "AI Agent Assistant - Conversation\n"
                conversation_text += "=" * 50 + "\n\n"
                
                for msg in st.session_state.messages:
                    role = msg["role"].upper()
                    content = msg["content"]
                    conversation_text += f"{role}:\n{content}\n\n"
                    conversation_text += "-" * 50 + "\n\n"
                
                st.download_button(
                    label="📥 Download TXT",
                    data=conversation_text,
                    file_name="conversation.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error preparing file: {str(e)}")
    
    with col_download3:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            try:
                conversation_text = ""
                for msg in st.session_state.messages:
                    role = msg["role"].upper()
                    content = msg["content"]
                    conversation_text += f"{role}:\n{content}\n\n"
                
                st.success("✅ Conversation copied! (Use Ctrl+V to paste)")
                st.code(conversation_text)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col_download4:
        if st.button("🔄 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.attached_doc = None
            st.session_state.doc_processed = False
            st.rerun()