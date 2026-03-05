import crew_config
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from typing import Optional
from pathlib import Path

from planner import plan_steps, planner_llm
from crew_orchestrator import run_crew


# ==============================
# FASTAPI APP
# ==============================
app = FastAPI()

# ✅ Custom audio endpoint with proper headers
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files with proper HTTP headers for streaming and seeking."""
    # Security: prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = Path("generated_audio") / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        filepath,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, must-revalidate",
        }
    )

# ==============================
# REQUEST MODEL

class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None
    image_context: Optional[dict] = None
    is_followup: bool = False
    # New: user-uploaded image for vision analysis
    input_image_b64: Optional[str] = None
    input_image_media_type: Optional[str] = None


class TTSRequest(BaseModel):
    text: str

# ==============================
# INTENT HELPERS
# ==============================
def user_wants_new_image(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in [
        "generate image",
        "create image",
        "draw",
        "show image",
        "image of",
        "picture of"
    ])

def refers_to_existing_image(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in [
        "this image",
        "above image",
        "that image",
        "the image",
        "given image",
        "this picture",
        "above picture"
    ])

# ==============================
# SEMANTIC HELPERS (LLM BASED)
# ==============================
def is_same_text_topic(previous_text: str | None, new_query: str) -> bool:
    if not previous_text:
        return False

    prompt = f"""
Answer ONLY YES or NO.

Previous explanation:
{previous_text}

New user question:
{new_query}

Question:
Does the new question DEPEND on the previous explanation to make sense?
"""
    try:
        resp = planner_llm.call([
            {"role": "system", "content": "You are a strict semantic classifier."},
            {"role": "user", "content": prompt}
        ])
        return resp.strip().upper().startswith("YES")
    except Exception:
        return False


def is_same_image_topic(image_context: dict | None, new_query: str) -> bool:
    if not image_context:
        return False

    prompt = f"""
Answer ONLY YES or NO.

Previously generated image description:
{image_context.get("semantic_hint", image_context.get("prompt", ""))}

New user request:
{new_query}

Question:
Is the new request referring to or dependent on the SAME image?
"""
    try:
        resp = planner_llm.call([
            {"role": "system", "content": "You are a strict semantic classifier."},
            {"role": "user", "content": prompt}
        ])
        return resp.strip().upper().startswith("YES")
    except Exception:
        return False


@app.post("/process-query")
async def process_query(req: QueryRequest):

    clean_query = req.query.strip()

    # ── VISION SHORT-CIRCUIT ─────────────────────────────────────────────────
    # If the user uploaded an image, route directly to VISION regardless of
    # any other intent logic.
    if req.input_image_b64:
        plan = {
            "steps": [
                {
                    "agent": "VISION",
                    "input": clean_query,
                    "image_b64": req.input_image_b64,
                    "image_media_type": req.input_image_media_type or "image/jpeg"
                }
            ]
        }

        print("\n========== DEBUG INTENT ==========")
        print("Detected intent: IMAGE_ANALYSIS (user uploaded image)")
        print("=================================\n")

        crew_result = run_crew(plan, clean_query)

        print("\n========== DEBUG CREW RESULT ==========")
        print(crew_result)
        print("======================================\n")

        # Store text response as context for follow-ups
        return {
            "text": crew_result.get("text", ""),
            "images": crew_result.get("images", []),
            "audio": crew_result.get("audio", None),
            "context": crew_result.get("text", None),
            "image_context": None
        }
    # ─────────────────────────────────────────────────────────────────────────

    wants_image = user_wants_new_image(clean_query)

    # ---------------------------------
    # SEMANTIC CHECKS
    # ---------------------------------
    same_text = is_same_text_topic(req.context, clean_query) if req.context else False
    same_image = is_same_image_topic(req.image_context, clean_query) if req.image_context else False
    refers_image = refers_to_existing_image(clean_query)

    print("\n========== DEBUG SEMANTIC ==========")
    print("Text context exists:", req.context is not None)
    print("Image context exists:", req.image_context is not None)
    print("User wants image:", wants_image)
    print("Same text topic:", same_text)
    print("Same image topic:", same_image)
    print("Refers to existing image:", refers_image)
    print("===================================\n")

    # ---------------------------------
    # FINAL INTENT DECISION
    # ---------------------------------
    if wants_image:
        intent = "IMAGE_REQUEST"
        req.context = None
        req.image_context = None

    elif req.image_context and refers_image:
        intent = "IMAGE_FOLLOWUP"

    elif same_image:
        intent = "IMAGE_FOLLOWUP"

    elif same_text:
        intent = "TEXT_FOLLOWUP"

    else:
        intent = "NEW_TOPIC"
        req.context = None
        req.image_context = None

    req.is_followup = intent in ("TEXT_FOLLOWUP", "IMAGE_FOLLOWUP")

    print("\n========== DEBUG INTENT ==========")
    print("Detected intent:", intent)
    print("=================================\n")

    
    # PLANNER INPUT
    
    planner_input = clean_query

    
    # PLANNER GUARDRAIL (TEXT-ONLY NEW TOPIC)
    
    if intent == "NEW_TOPIC" and not wants_image and not req.image_context:
        planner_input = f"""
This is a TEXT-ONLY request.
DO NOT generate images.

User request:
{clean_query}
"""

    if intent == "TEXT_FOLLOWUP":
        planner_input = f"""
Previous explanation:
{req.context}

The user is asking a FOLLOW-UP question.
DO NOT change topic.

User request:
{clean_query}
"""

    elif intent == "IMAGE_FOLLOWUP":
        planner_input = f"""
An image has already been generated.

Image description:
{req.image_context.get("semantic_hint", req.image_context.get("prompt", ""))}

The user is asking a FOLLOW-UP question.
DO NOT generate a new image.

User request:
{clean_query}
"""

    print("\n========== DEBUG PLANNER INPUT ==========")
    print(planner_input)
    print("========================================\n")

    plan = plan_steps(planner_input)

    print("\n========== DEBUG PLANNER OUTPUT ==========")
    print(plan)
    print("=========================================\n")

    
    #  HARD LOCK IMAGE ON IMAGE FOLLOW-UP

    if intent == "IMAGE_FOLLOWUP":
        plan["steps"] = [
            step for step in plan.get("steps", [])
            if step.get("agent") != "IMAGE"
        ]

    if not plan.get("steps"):
        plan["steps"] = [{"agent": "TEXT", "input": clean_query}]

    print("\n========== DEBUG PLAN AFTER LOCK ==========")
    print(plan)
    print("==========================================\n")

    
    # 🚀 EXECUTION QUERY

    execution_query = clean_query

    if intent == "TEXT_FOLLOWUP":
        execution_query += f"""
Previous explanation:
{req.context}

Answer in continuation.
"""

    if intent == "IMAGE_FOLLOWUP":
        execution_query += f"""
CRITICAL IMAGE CONTEXT:
An image HAS ALREADY BEEN GENERATED.

RULES:
- DO NOT generate a new image
- ONLY explain the existing image
"""

    print("\n========== DEBUG EXECUTION QUERY ==========")
    print(execution_query)
    print("==========================================\n")

    
    # 🤖 RUN CREW
    
    crew_result = run_crew(plan, execution_query)

    print("\n========== DEBUG CREW RESULT ==========")
    print(crew_result)
    print("======================================\n")

    return {
        "text": crew_result.get("text", ""),
        "images": crew_result.get("images", []),
        "audio": crew_result.get("audio", None),
        "context": crew_result.get("text", None),
        "image_context": req.image_context
    }


# RUN SERVER

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)