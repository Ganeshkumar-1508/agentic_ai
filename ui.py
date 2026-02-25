import streamlit as st
import requests
from fpdf import FPDF
import os
import re

FASTAPI_URL = "http://localhost:8000"

# ================= PDF EXPORT =================
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


# ================= UI =================
st.set_page_config(page_title="AI Agent Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Chat with AI Assistant")
st.caption("Chat with AI by giving a query")

# Backend check
try:
    requests.get(f"{FASTAPI_URL}/docs", timeout=3)
except Exception:
    st.error("❌ Backend not running. Start with: python api.py")
    st.stop()

# ================= SESSION STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_text_context" not in st.session_state:
    st.session_state.last_text_context = None

if "last_image_context" not in st.session_state:
    st.session_state.last_image_context = None

if "last_audio_path" not in st.session_state:
    st.session_state.last_audio_path = None

# ================= CHAT HISTORY =================
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            st.image(msg["content"], width=350)

# ================= INPUT (MUST BE LAST) =================
prompt = st.chat_input("Ask anything")

if prompt:
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Generating..."):

            is_followup = st.session_state.last_image_context is not None

            response = requests.post(
                f"{FASTAPI_URL}/process-query",
                json={
                    "query": prompt,
                    "context": st.session_state.last_text_context,
                    "image_context": st.session_state.last_image_context,
                    "is_followup": is_followup
                },
                timeout=400
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

            # 🔊 store audio (manual play only)
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

# ================= DOWNLOADS + MIC =================
if st.session_state.messages:
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)

    # 📄 PDF
    with col1:
        st.download_button(
            "📄 Download PDF",
            generate_pdf_from_conversation(st.session_state.messages),
            "conversation.pdf"
        )

    # 📋 TXT
    with col2:
        txt = ""
        for m in st.session_state.messages:
            if m["type"] == "text":
                txt += f"{m['role'].upper()}:\n{m['content']}\n\n"
        st.download_button("📋 Download TXT", txt, "conversation.txt")

    # ⧉ COPY (YOUR ORIGINAL CODE – UNTOUCHED)
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

    # 🔄 CLEAR
    with col4:
        if st.button("🔄 Clear Chat"):
            st.session_state.messages = []
            st.session_state.last_audio_path = None
            st.rerun()

    # 🎤 MIC (ONLY ADDITION)
    with col5:
        if st.session_state.last_audio_path:
            if st.button("🎤 Play Audio"):
                audio_url = f"{FASTAPI_URL}/{st.session_state.last_audio_path}".replace("\\", "/")
                st.audio(audio_url, format="audio/mp3")
        else:
            st.empty()