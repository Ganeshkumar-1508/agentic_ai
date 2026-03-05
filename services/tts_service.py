import os
import uuid
import re
import io
import wave
import time
import random

print("LOADED NVIDIA MAGPIE TTS (gRPC / RIVA)")
print("🎧 OUTPUT FORMAT: WAV ONLY")


# PATHS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "generated_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)



# Helper for years
def year_to_speech(val):
    """
    Converts a year (e.g., 2022) into 'twenty twenty two'
    instead of 'two thousand twenty two' to prevent 
    'January 2' -> 'January second' issues.
    """
    if 1900 <= val <= 1999:
        prefix = "nineteen"
        remainder = val - 1900
    elif 2000 <= val <= 2099:
        prefix = "twenty"
        remainder = val - 2000
    else:
        # Fallback for non-standard years
        return number_to_speech_recursive(val)

    # Handle 2000, 1900 exactly
    if remainder == 0:
        return prefix + " hundred" if val < 2000 else "two thousand"
    
    # Handle 2001-2009 (two thousand [and] five)
    if 0 < remainder < 10:
        return f"two thousand {number_to_speech_recursive(remainder)}"
    
    # Handle 1910-1999, 2010-2099 (nineteen eighty four, twenty twenty two)
    return f"{prefix} {number_to_speech_recursive(remainder)}"


def number_to_speech_recursive(val):
    """
    Recursively converts any integer into a speakable string.
    e.g., 48500 -> "48 thousand 500"
    """
    if val == 0:
        return ""

    # Indian System: Lakhs
    if val >= 100000:
        lakh = val // 100000
        remainder = val % 100000
        text = f"{lakh} lakh"
        if remainder > 0:
            text += " " + number_to_speech_recursive(remainder)
        return text

    # International System: Thousands
    if val >= 1000:
        thousand = val // 1000
        remainder = val % 1000
        text = f"{thousand} thousand"
        if remainder > 0:
            text += " " + number_to_speech_recursive(remainder)
        return text

    # Hundreds
    if val >= 100:
        hundred = val // 100
        remainder = val % 100
        text = f"{hundred} hundred"
        if remainder > 0:
            text += " " + number_to_speech_recursive(remainder)
        return text

    # Below 100: Return digits (TTS reads "25" as "twenty five")
    return str(val)


def normalize_text_for_tts(text: str) -> str:
    """
    Normalizes text to prevent TTS crashes and fix number reading.
    """
    
    # 1. DYNAMIC CURRENCY MAPPING
    currency_map = {
        "$": "dollars", "₹": "rupees", "€": "euros", 
        "£": "pounds", "¥": "yen", "₽": "rubles"
    }
    
    for symbol, name in currency_map.items():
        if symbol in text:
            text = text.replace(symbol, f" {name} ")

    # 2. Other Symbols
    text = text.replace("%", " percent ")
    text = text.replace("&", " and ")
    
    # CRITICAL FIX: Smart Colon Handling
    # A. Replace ratios like 1:2.33 with " to "
    text = re.sub(r"(\d)\s*:\s*(\d)", r"\1 to \2", text)
    
    # B. Replace label colons (e.g., "Rate:") with period or remove to prevent crash
    # This prevents "Rate: Money" -> "Rate to Money"
    text = text.replace(":", ". ")

    # 3. FIX SLASHES (7/10 -> 7 out of 10)
    text = re.sub(r"(\d)\s*/\s*(\d)", r"\1 out of \2", text)

    # 4. Remove commas inside numbers (Handle Indian format: 1,25,000 -> 125000)
    while True:
        new_text = re.sub(r"(\d)\s*,\s*(\d)", r"\1\2", text)
        if new_text == text:
            break
        text = new_text

    # 5. Fix Decimals (1.5 -> 1 point 5)
    text = re.sub(r"(\d)\.(\d)", r"\1 point \2", text)

    # 6. ROBUST NUMBER TO WORD HELPER
    def number_replacer(match):
        num_str = match.group(0)
        try:
            val = int(num_str)
            
            # FIX: Handle YEARS specifically (1900-2099)
            # This prevents "January 2022" -> "January 2 thousand..." -> "January second..."
            if 1900 <= val <= 2099:
                return year_to_speech(val)

            # Convert ANY number >= 100 into words
            if val >= 100:
                return number_to_speech_recursive(val)
        except ValueError:
            pass
        return num_str

    # Apply to sequences of 3+ digits
    text = re.sub(r'\b\d{3,}\b', number_replacer, text)

    return text.strip()



# CLEAN TEXT FOR TTS

def clean_text_for_tts(text: str) -> str:
    # 1. Strip ALL HTML/XML Tags
    text = re.sub(r"<[^>]+>", "", text)

    # 2. Remove Setext-style headers (underlines)
    text = re.sub(r"^\s*={3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.MULTILINE)

    # 3. Remove Header hashes (#)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)

    # 4. Remove Bold/Italic markers
    text = text.replace("**", "").replace("__", "")
    
    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    
    lines = text.splitlines()
    cleaned_lines = []
    inside_code_block = False

    for line in lines:
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith("```"):
            inside_code_block = not inside_code_block
            continue
        if inside_code_block:
            continue

        if not stripped:
            continue

        # Filter Leaked Code Lines
        if re.match(r"^\s*(def|class|import|from|return|if|else|elif|for|while|try|catch|finally|with|as|print|console|public|private|void|int|string|bool|return)\b", stripped):
            continue
        if re.search(r"[{};]", stripped):
            continue
        if re.search(r"::|->", stripped):
            continue

        # Remove Bullet Points
        stripped = re.sub(r"^\s*[\*\-\•]\s+", "", stripped)

        # TABLE HANDLING
        if "|" in stripped:
            # Skip table separator lines
            if re.match(r'^[\|\-\s]+$', stripped):
                continue
            # Clean table rows
            stripped = stripped.strip("|")
            stripped = stripped.replace("|", ", ")

        # Add Punctuation for Pauses
        if not re.search(r"[.!?]$", stripped):
            stripped += "."

        # Normalize line (Numbers, Symbols)
        stripped = normalize_text_for_tts(stripped)

        cleaned_lines.append(stripped)

    # Join paragraphs with double Newlines
    result = "\n\n".join(cleaned_lines).strip()

    # Fallback
    if not result:
        fallback = re.sub(r"[`#*_\\|]", "", text)
        fallback = re.sub(r"\s+", " ", fallback).strip()
        result = fallback[:300] if fallback else "Here is the generated response."
        result = normalize_text_for_tts(result)

    return result


def split_text(text: str, max_chars: int = 500): # Reduced from 1200
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if current_chunk:
            potential_chunk = current_chunk + "\n\n" + para
        else:
            potential_chunk = para
            
        if len(potential_chunk) <= max_chars:
            current_chunk = potential_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            if len(para) <= max_chars:
                current_chunk = para
            else:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_chunk = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence: continue
                    
                    if len(temp_chunk) + len(sentence) + 1 <= max_chars:
                        temp_chunk += " " + sentence if temp_chunk else sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        
                        if len(sentence) > max_chars:
                            chunks.append(sentence[:max_chars])
                            temp_chunk = sentence[max_chars:]
                        else:
                            temp_chunk = sentence
                            
                if temp_chunk:
                    current_chunk = temp_chunk

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text.strip()]



# PCM → WAV

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 22050) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buffer.getvalue()



def generate_speech(text: str) -> str:
    print("🔊 EXECUTING MAGPIE TTS (gRPC Direct)")

    if not text or not text.strip():
        raise ValueError("No text provided for TTS")

    clean_text = clean_text_for_tts(text)
    print(f"📝 Cleaned text: {len(clean_text)} chars")
    
    if clean_text == "Here is the generated response.":
        print("⚠️ Warning: Input text was entirely filtered out. Using fallback.")

    chunks = split_text(clean_text, max_chars=500)
    print(f"📊 Split into {len(chunks)} chunks")

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise EnvironmentError("NVIDIA_API_KEY not set")

    try:
        import grpc
        from riva.client.proto.riva_audio_pb2 import AudioEncoding
        from riva.client.proto.riva_tts_pb2 import SynthesizeSpeechRequest
        from riva.client.proto.riva_tts_pb2_grpc import RivaSpeechSynthesisStub

        channel_options = [
            ("grpc.max_receive_message_length", -1),
            ("grpc.max_send_message_length", -1),
            ("grpc.client_idle_timeout_ms", 60000),
        ]
        ssl_creds = grpc.ssl_channel_credentials()
        call_creds = grpc.metadata_call_credentials(
            lambda _ctx, cb: cb(
                [("function-id", "877104f7-e885-42b9-8de8-f6e4c6303969"),
                 ("authorization", f"Bearer {api_key}")],
                None,
            )
        )
        channel = grpc.secure_channel(
            "grpc.nvcf.nvidia.com:443",
            grpc.composite_channel_credentials(ssl_creds, call_creds),
            options=channel_options,
        )
        stub = RivaSpeechSynthesisStub(channel)

        pcm_audio = b""
        successful_chunks = 0

        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk: continue
            
            print(f"🎙️ Chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
            print(f"📝 Content: {chunk[:80]}...")

            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    request = SynthesizeSpeechRequest(
                        text=chunk,
                        voice_name="Magpie-Multilingual.EN-US.Aria",
                        language_code="en-US",
                        encoding=AudioEncoding.LINEAR_PCM,
                        sample_rate_hz=22050,
                    )
                    
                    resp = stub.Synthesize(request, timeout=30)
                    
                    if resp and resp.audio:
                        pcm_audio += resp.audio
                        successful_chunks += 1
                        print(f"✅ Chunk {i+1} synthesized: {len(resp.audio)} bytes")
                        break 
                    else:
                        print(f"⚠️ Chunk {i+1} returned empty audio, retrying...")
                        time.sleep(retry_delay)
                        
                except Exception as chunk_error:
                    error_str = str(chunk_error)
                    print(f"❌ Chunk {i+1} Attempt {attempt+1} failed: {error_str[:100]}")
                    
                    if "StatusCode.UNKNOWN" in error_str or "DEADLINE_EXCEEDED" in error_str:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1) + random.randint(0, 2)
                            print(f"⏳ Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"❌ Chunk {i+1} failed after {max_retries} retries")
                            raise Exception(f"TTS failed on chunk {i+1}: {error_str[:100]}")
                    else:
                        raise

        if successful_chunks == 0:
            raise ValueError("No chunks were successfully synthesized")

        print(f"✅ All {successful_chunks} chunks synthesized successfully")

        wav_audio = pcm_to_wav(pcm_audio)
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(wav_audio)

        print(f"✅ WAV GENERATED: {filepath} ({len(wav_audio)} bytes)")
        return os.path.relpath(filepath, BASE_DIR).replace("\\", "/")

    except Exception as e:
        print(f"❌ TTS Error: {str(e)[:200]}")
        raise