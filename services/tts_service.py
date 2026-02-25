import os
import uuid
import re
from gtts import gTTS

# ===============================
# PATHS
# ===============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")


# ===============================
# MARKDOWN STRIPPER (HEADINGS ONLY)
# ===============================
def strip_markdown_for_heading(text: str) -> str:
    """
    Remove ALL markdown symbols from headings / sub-headings ONLY
    """
    text = re.sub(r"^\s*#{1,6}\s*", "", text)   # ### Heading
    text = re.sub(r"[*_`]+", "", text)          # ** __ `
    text = text.replace("\\", "")
    return text.strip()


# ===============================
# CLEAN TEXT FOR TTS
# ===============================
def clean_text_for_tts(text: str) -> str:
    
    """
    FINAL, PERMANENT, LLM-SAFE TTS CLEANER

    ✅ Reads first heading
    ✅ Reads all headings (including Conclusion)
    ❌ Never reads bullets (*, -, •)
    ❌ Never reads code blocks
    ❌ Never reads code-like lines
    ❌ Never reads markdown symbols in headings
    """
    # 🔥 Normalize escaped unicode & newlines
    text = (
        text.encode("utf-8")
            .decode("unicode_escape")
    )
    lines = text.splitlines()
    cleaned_lines = []

    inside_code_block = False
    i = 0
    total = len(lines)

    while i < total:
        raw_line = lines[i]
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        # ===============================
        # DEBUG
        # ===============================
        print(f"[TTS DEBUG] LINE {i}: {repr(stripped)}")

        # ===============================
        # 1. CODE BLOCK HANDLING (ABSOLUTE)
        # ===============================
        if stripped.startswith("```"):
            inside_code_block = not inside_code_block
            print("  -> TOGGLE CODE BLOCK:", inside_code_block)
            i += 1
            continue

        if inside_code_block:
            print("  -> SKIP (inside code block)")
            i += 1
            continue

        # ===============================
        # 2. FIRST HEADING (ONLY ONCE)
        # ===============================
        if not cleaned_lines and stripped:
            cleaned_lines.append(strip_markdown_for_heading(stripped) + ".")
            print("  -> FIRST HEADING:", stripped)
            i += 1
            continue

        # ===============================
        # 3. NORMALIZE BULLETS
        # ===============================
        line = re.sub(r"^\s*[\*\-\•]\s+", "", line)
        stripped = line.strip()

        # ===============================
        # 4. UNDERLINE HEADING
        # ===============================
        if (
            stripped
            and i + 1 < total
            and re.match(r"^[=\-]{3,}$", lines[i + 1].strip())
        ):
            cleaned_lines.append(strip_markdown_for_heading(stripped) + ".")
            print("  -> UNDERLINE HEADING:", stripped)
            i += 2
            continue

        # ===============================
        # 5. GLUED HEADING (Title====)
        # ===============================
        m = re.match(r"^(.*?)([=\-]{3,})$", stripped)
        if m:
            heading = m.group(1).strip()
            if heading:
                cleaned_lines.append(strip_markdown_for_heading(heading) + ".")
                print("  -> GLUED HEADING:", heading)
            i += 1
            continue

        # ===============================
        # 6. STRUCTURAL HEADING (SAFE)
        # ===============================
        if (
            stripped
            and i + 1 < total
            and lines[i + 1].strip() == ""
            and len(stripped.split()) <= 6
            and not stripped.endswith((".", ":"))
            and not re.match(r"^\d+\.", stripped)
        ):
            cleaned_lines.append(strip_markdown_for_heading(stripped) + ".")
            print("  -> STRUCTURAL HEADING:", stripped)
            i += 1
            continue

        # ===============================
        # 7. CODE-LIKE LINE SKIP
        # ===============================
        if (
            stripped.startswith(("    ", "\t"))
            or stripped.endswith(("{", "}", ";"))
            or re.match(r"^[\w<>\[\]\(\)\.=:+\-/*%&|!]+$", stripped)
        ):
            print("  -> SKIP (code-like)")
            i += 1
            continue

        # ===============================
        # 8. FINAL CLEANUP (EXPLANATIONS)
        # ===============================
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        line = (
            line.replace("**", "")
                .replace("__", "")
                .replace("`", "")
                .replace("\\", "")
        )

        if line.strip():
            cleaned_lines.append(line)
            print("  -> ADD TEXT")

        i += 1

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{2,}", "\n", result)

    print("\n===== CLEANED TEXT FOR TTS =====")
    print(result)
    print("================================\n")

    return result.strip()


# ===============================
# GENERATE SPEECH
# ===============================
def generate_speech(text: str) -> str:
    """
    Convert cleaned text to speech using gTTS
    """

    print("\n===== RAW TEXT RECEIVED BY TTS =====")
    print(text)
    print("===================================\n")

    if not text or not text.strip():
        raise ValueError("No text provided for text-to-speech")

    clean_text = clean_text_for_tts(text)

    if not clean_text:
        raise ValueError("Text became empty after cleaning")

    os.makedirs(AUDIO_DIR, exist_ok=True)

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    tts = gTTS(text=clean_text, lang="en", slow=False)
    tts.save(filepath)

    return os.path.relpath(filepath, BASE_DIR).replace("\\", "/")