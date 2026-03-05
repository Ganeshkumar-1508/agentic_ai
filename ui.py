import streamlit as st
import requests
from fpdf import FPDF
import os
import re
import base64
from PIL import Image
import io
from io import BytesIO

FASTAPI_URL = "http://localhost:8000"

def get_last_text_context():
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and msg["type"] == "text":
            return msg["content"]
    return None


#  PDF EXPORT 

def add_markdown_text(pdf, text):
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    lines = text.split("\n")
    in_code_block = False

    for line in lines:
        clean = line.rstrip()

        if clean.startswith("```"):
            in_code_block = not in_code_block
            pdf.ln(4)
            continue

        pdf.set_x(pdf.l_margin)

        if in_code_block:
            pdf.set_font("DejaVu", "", 10)
            pdf.set_fill_color(245, 245, 245)
            pdf.multi_cell(usable_width, 6, clean)
            continue

        if clean.startswith("### "):
            pdf.set_font("DejaVu", "B", 16)
            pdf.multi_cell(usable_width, 8, clean[4:])
            pdf.ln(2)

        elif clean.startswith("## "):
            pdf.set_font("DejaVu", "B", 18)
            pdf.multi_cell(usable_width, 10, clean[3:])
            pdf.ln(3)

        elif clean.startswith("# "):
            pdf.set_font("DejaVu", "B", 22)
            pdf.multi_cell(usable_width, 12, clean[2:])
            pdf.ln(4)

        elif clean.startswith("* ") or clean.startswith("- "):
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(usable_width, 6, "• " + clean[2:])

        elif "**" in clean:
            parts = re.split(r"(\*\*.*?\*\*)", clean)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    pdf.set_font("DejaVu", "B", 11)
                    pdf.write(6, part[2:-2])
                else:
                    pdf.set_font("DejaVu", "", 11)
                    pdf.write(6, part)
            pdf.ln(8)

        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(usable_width, 6, clean)


def generate_pdf_from_conversation(messages):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    pdf.add_font("DejaVu", "", os.path.join(BASE_DIR, "dejavu-fonts-ttf-2.37", "ttf", "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", os.path.join(BASE_DIR, "dejavu-fonts-ttf-2.37", "ttf", "DejaVuSans-Bold.ttf"))

    pdf.add_page()
    pdf.set_font("DejaVu", "", 11)

    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 12, "AI Agent Assistant - Conversation", ln=True, align="C")
    pdf.ln(8)

    for msg in messages:
        role = msg["role"].upper()

        if msg["type"] == "text":
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, role, ln=True)
            pdf.ln(2)
            add_markdown_text(pdf, msg["content"])
            pdf.ln(6)

        elif msg["type"] == "image" and os.path.exists(msg["content"]):
            pdf.image(msg["content"], w=pdf.w - pdf.l_margin - pdf.r_margin)
            pdf.ln(8)

    return bytes(pdf.output(dest="S"))


def encode_image_to_base64(uploaded_file) -> str:
    """Encode a Streamlit uploaded file to base64 string."""
    bytes_data = uploaded_file.read()
    # Reset pointer so it can be displayed again
    uploaded_file.seek(0)
    return base64.b64encode(bytes_data).decode("utf-8")


def get_image_media_type(uploaded_file) -> str:
    """Derive MIME type from file extension."""
    name = uploaded_file.name.lower()
    if name.endswith(".png"):
        return "image/png"
    elif name.endswith(".jpg") or name.endswith(".jpeg"):
        return "image/jpeg"
    elif name.endswith(".gif"):
        return "image/gif"
    elif name.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


# UI 

st.set_page_config(page_title="AI Agent Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Chat with AI Assistant")
st.caption("Chat with AI by giving a query — or upload an image for analysis")

# Backend check
try:
    requests.get(f"{FASTAPI_URL}/docs", timeout=3)
except Exception:
    st.error("❌ Backend not running. Start with: python api.py")
    st.stop()

#SESSION STATE

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_text_context" not in st.session_state:
    st.session_state.last_text_context = None

if "last_image_context" not in st.session_state:
    st.session_state.last_image_context = None

if "last_audio_path" not in st.session_state:
    st.session_state.last_audio_path = None

#  CHAT HISTORY 
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            st.image(msg["content"], width=350)
        elif msg["type"] == "uploaded_image":
            # Display user-uploaded images inline in history
            st.image(msg["content"], width=350, caption="📎 Uploaded image")

# IMAGE UPLOAD WIDGET 
with st.expander("📎 Attach an image for analysis", expanded=False):
    uploaded_image = st.file_uploader(
        "Upload an image (PNG, JPG, JPEG, WEBP, GIF)",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        key="image_uploader"
    )
    if uploaded_image:
        st.image(uploaded_image, width=300, caption="Preview — ask a question below to analyse this image")

#INPUT

prompt = st.chat_input("Ask anything (or ask about the uploaded image)")

if prompt:
    #  Encode uploaded image if present 
    st.session_state.last_audio_path = None
    image_b64 = None
    image_media_type = None
    if uploaded_image is not None:
        image_b64 = encode_image_to_base64(uploaded_image)
        image_media_type = get_image_media_type(uploaded_image)
    
    
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    # If the user attached an image, also log it in history
    if image_b64:
        # Store raw bytes for display (re-read from upload)
        raw_bytes = base64.b64decode(image_b64)
        pil_img = Image.open(io.BytesIO(raw_bytes))
        # We keep it as a PIL image reference; for history we'll store b64
        st.session_state.messages.append({
            "role": "user",
            "type": "uploaded_image",
            "content": pil_img   # PIL image renders fine with st.image
        })

    with st.chat_message("user"):
        st.markdown(prompt)
        if image_b64:
            st.image(Image.open(io.BytesIO(base64.b64decode(image_b64))), width=300)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Generating..."):

            is_followup = st.session_state.last_image_context is not None

            response = requests.post(
                f"{FASTAPI_URL}/process-query",
                json={
                    "query": prompt,
                    "context": st.session_state.last_text_context,
                    "image_context": st.session_state.last_image_context,
                    "is_followup": is_followup,
                    # New fields for vision:
                    "input_image_b64": image_b64,
                    "input_image_media_type": image_media_type
                },
                timeout=600
            )

            if response.status_code != 200:
                st.error("❌ Backend error occurred. Check FastAPI logs.")
                st.stop()

            data = response.json()
            text = data.get("text", "")
            images = data.get("images", [])
            audio = data.get("audio")

            if text:
                st.markdown(text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": text
                })

            # store audio path
            st.session_state.last_audio_path = audio if audio else None

            if text and not images:
                st.session_state.last_text_context = text
            else:
                st.session_state.last_text_context = None

            if images:
                st.markdown("🖼️ **Generated Image:**")
                for img_path in images:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "image",
                        "content": img_path
                    })
                    st.image(img_path, width=350)

                st.session_state.last_image_context = {
                    "prompt": prompt,
                    "final_image": images[-1],
                    "semantic_hint": prompt
                }
            else:
                st.session_state.last_image_context = None

#  DOWNLOADS + MIC
if st.session_state.messages:
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)

    # PDF
    with col1:
        # Filter only serialisable messages for PDF
        pdf_messages = [m for m in st.session_state.messages if m["type"] in ("text", "image")]
        st.download_button(
            "📄 Download PDF",
            generate_pdf_from_conversation(pdf_messages),
            "conversation.pdf"
        )

    # TXT
    with col2:
        txt = ""
        for m in st.session_state.messages:
            if m["type"] == "text":
                txt += f"{m['role'].upper()}:\n{m['content']}\n\n"
        st.download_button("📋 Download TXT", txt, "conversation.txt")

    # COPY
    with col3:
        clipboard_text = ""
        for m in st.session_state.messages:
            if m["type"] == "text":
                clipboard_text += f"{m['role'].upper()}:\n{m['content']}\n\n"

        escaped_text = (
            clipboard_text
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("$", "\\$")
        )

        st.components.v1.html(
            f"""
            <div style="text-align:left;">
                <button onclick="copyText()" style="background:none;border:none;cursor:pointer;font-size:18px;">
                    ⧉ Copy
                </button>
            </div>
            <script>
            function copyText() {{
                navigator.clipboard.writeText(`{escaped_text}`);
            }}
            </script>
            """,
            height=40
        )

    # CLEAR
    with col4:
        if st.button("🔄 Clear Chat"):
            st.session_state.messages = []
            st.rerun()
            st.session_state.last_audio_path = None
            st.rerun()

    # AUDIO PLAYER (FIXED - BYTES-BASED)
    with col5:
        if st.session_state.last_audio_path:
            if st.button("🎤 Play Audio"):
                try:
                    # Extract filename from path
                    filename = st.session_state.last_audio_path.split("/")[-1]
                    audio_url = f"{FASTAPI_URL}/audio/{filename}"
                    
                    # Fetch audio as bytes (fixes truncation issue)
                    response = requests.get(audio_url, timeout=60)
                    if response.status_code == 200:
                        st.audio(BytesIO(response.content), format="audio/wav")
                    else:
                        st.error(f"❌ Failed to load audio (HTTP {response.status_code})")
                except requests.Timeout:
                    st.error("❌ Audio download timeout (>60 seconds)")
                except Exception as e:
                    st.error(f"❌ Audio error: {str(e)[:100]}")
        else:
            st.empty()
