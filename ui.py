import streamlit as st
import requests
from fpdf import FPDF
import os
import time
import re

FASTAPI_URL = "http://localhost:8000"

def get_last_text_context():
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and msg["type"] == "text":
            return msg["content"]
    return None


# ================= IMAGE JOB POLLING (SINGLE SOURCE OF TRUTH) =================
def poll_image_jobs_once():
    updated = False

    for i, msg in enumerate(st.session_state.messages):
        if msg["type"] == "image_job":
            job_id = msg["content"]

            try:
                status = requests.get(
                    f"{FASTAPI_URL}/image-status/{job_id}",
                    timeout=3
                ).json()

                if status["status"] == "done":
                    st.session_state.messages[i] = {
                        "role": "assistant",
                        "type": "image",
                        "content": status["image_path"]
                    }
                    updated = True

                elif status["status"] == "failed":
                    st.session_state.messages[i] = {
                        "role": "assistant",
                        "type": "text",
                        "content": "❌ Image generation failed"
                    }
                    updated = True

            except Exception:
                pass

    return updated


# ================= PDF EXPORT =================
def add_markdown_text(pdf, text):
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    lines = text.split("\n")

    in_code_block = False

    for line in lines:
        clean = line.rstrip()

        # Toggle code block
        if clean.startswith("```"):
            in_code_block = not in_code_block
            pdf.ln(4)
            continue

        pdf.set_x(pdf.l_margin)

        # ===== CODE BLOCK =====
        if in_code_block:
            pdf.set_font("DejaVu", "", 10)
            pdf.set_fill_color(245, 245, 245)
            pdf.multi_cell(usable_width, 6, clean)
            continue

        # ===== HEADINGS =====
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

        # ===== BULLETS =====
        elif clean.startswith("* ") or clean.startswith("- "):
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(usable_width, 6, "• " + clean[2:])

        # ===== BOLD TEXT =====
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

        # ===== NORMAL TEXT =====
        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(usable_width, 6, clean)

def generate_pdf_from_conversation(messages):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    font_path_regular = os.path.join(
        BASE_DIR,
        "dejavu-fonts-ttf-2.37",
        "ttf",
        "DejaVuSans.ttf"
    )

    font_path_bold = os.path.join(
        BASE_DIR,
        "dejavu-fonts-ttf-2.37",
        "ttf",
        "DejaVuSans-Bold.ttf"
    )

    pdf.add_font("DejaVu", "", font_path_regular)
    pdf.add_font("DejaVu", "B", font_path_bold)

    pdf.add_page()
    pdf.set_font("DejaVu", "", 11)

    # Title
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 12, "AI Agent Assistant - Conversation", ln=True, align="C")
    pdf.ln(8)

    for msg in messages:
        role = msg["role"].upper()
        msg_type = msg["type"]

        if msg_type == "text":

            # Role Header Styling
            pdf.set_font("DejaVu", "B", 12)

            if role == "USER":
                pdf.set_text_color(0, 0, 180)  # Blue
            else:
                pdf.set_text_color(0, 140, 0)  # Green

            pdf.cell(0, 8, role, ln=True)
            pdf.set_text_color(0, 0, 0)

            pdf.ln(2)

            add_markdown_text(pdf, msg["content"])
            pdf.ln(6)

        elif msg_type == "image":
            image_path = msg["content"]
            if os.path.exists(image_path):
                usable_width = pdf.w - pdf.l_margin - pdf.r_margin
                pdf.image(image_path, w=usable_width)
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


# ✅ SINGLE POLL LOCATION
if poll_image_jobs_once():
    st.rerun()


# ================= CHAT HISTORY =================
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):

        if msg["type"] == "text":
            st.markdown(msg["content"])

        elif msg["type"] == "image":
            st.image(msg["content"], width=350)

        elif msg["type"] == "image_job":
            st.info("🖼️ Generating image… please wait")


# ================= INPUT =================
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
            context = get_last_text_context()

            response = requests.post(
                f"{FASTAPI_URL}/process-query",
                json={
                    "query": prompt,
                    "context": context,
                    "image_context": st.session_state.get("last_image_context")
                },
                timeout=300
            )


            data = response.json()
            text = data.get("text", "")
            images = data.get("images", [])

            if text and not text.startswith("⚠️"):
                st.markdown(text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": text
                })

            if images and (not text or text.startswith("⚠️")):
                st.markdown("🖼️ **Here is the image you requested:**")

            for job_id in images:
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "image_job",
                    "content": job_id
                })
            # ✅ STORE IMAGE CONTEXT FOR FUTURE QUESTIONS
            st.session_state.last_image_context = {
                "prompt": prompt,     # what user asked to generate
                "job_ids": images     # optional, for future use
            }


# ================= DOWNLOADS =================
if st.session_state.messages:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pdf_data = generate_pdf_from_conversation(st.session_state.messages)
        st.download_button("📄 Download PDF", pdf_data, "conversation.pdf")

    with col2:
        txt = ""
        for m in st.session_state.messages:
            if m["type"] == "text":
                txt += f"{m['role'].upper()}:\n{m['content']}\n\n"

        st.download_button("📋 Download TXT", txt, "conversation.txt")

    with col3:
        clipboard_text = ""

        for m in st.session_state.messages:
            if m["type"] == "text":
                clipboard_text += f"{m['role'].upper()}:\n{m['content']}\n\n"

        # Escape properly for JS
        escaped_text = (
            clipboard_text
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("$", "\\$")
        )

        st.components.v1.html(f"""
            <div style="text-align:left;">
                <button onclick="copyText()" 
                    style="
                        background:none;
                        border:none;
                        cursor:pointer;
                        font-size:18px;
                    ">
                    ⧉
                </button>
            </div>

            <script>
            function copyText() {{
                navigator.clipboard.writeText(`{escaped_text}`);
            }}
            </script>
        """, height=40)


    with col4:
        if st.button("🔄 Clear Chat"):
            st.session_state.messages = []
            st.rerun()
# ================= FORCE UI REFRESH WHILE IMAGE IS PENDING =================
if any(msg["type"] == "image_job" for msg in st.session_state.messages):
    time.sleep(2)
    st.rerun()
