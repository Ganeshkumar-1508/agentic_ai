# image_agent.py
import os
import uuid
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

# ==============================
# LOCAL CPU IMAGE MODEL (FASTEST SAFE OPTION)
# ==============================
MODEL_ID = "runwayml/stable-diffusion-v1-5"
DEVICE = "cpu"

print("🔄 Loading Stable Diffusion 1.5 (CPU)...")

pipe = StableDiffusionPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    safety_checker=None
)

pipe = pipe.to(DEVICE)

# ✅ SPEED OPTIMIZATIONS
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe.enable_attention_slicing()

print("✅ Model loaded successfully")


def generate_image(prompt: str) -> dict | None:
    """
    Generates image locally using CPU.
    Optimized for speed.
    """
    try:
        image = pipe(
            prompt=prompt,
            num_inference_steps=15,     # ↓ from 30
            guidance_scale=6.0,         # ↓ slightly
            height=384,                 # ↓ resolution
            width=384
        ).images[0]

        os.makedirs("generated_images", exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        image_path = os.path.join("generated_images", filename)

        image.save(image_path)

        return {"image_path": image_path}

    except Exception as e:
        print("[IMAGE_AGENT ERROR]", str(e))
        return None


# ==============================
# CLI TEST
# ==============================
if __name__ == "__main__":
    print("🖼️ Testing optimized CPU image generation...")
    result = generate_image(
        "butterfly life cycle diagram, educational, labeled, clean background"
    )

    if result:
        print("✅ Image generated at:", result["image_path"])
    else:
        print("❌ Image generation failed")
