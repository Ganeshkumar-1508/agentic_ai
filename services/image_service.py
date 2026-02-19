from fileinput import filename
import os
import requests
import uuid
import time


AI_HORDE_API = "https://aihorde.net/api/v2/generate/async"
AI_HORDE_CHECK = "https://aihorde.net/api/v2/generate/status/"

HEADERS = {
    "Content-Type": "application/json",
    "apikey": "0000000000",  # anonymous key (fully free)
    "Client-Agent": "crew-ai-app:1.0"
}


def generate_image(prompt: str):
    """
    Keeping function name same so no other code changes.
    Now internally uses AI Horde.
    """

    payload = {
        "prompt": prompt,
        "params": {
            "width": 512,
            "height": 512,
            "steps": 25
        },
        "nsfw": False,
        "models": ["stable_diffusion"]
    }

    # Step 1: Send generation request
    response = requests.post(AI_HORDE_API, json=payload, headers=HEADERS)

    if response.status_code != 202:
        return {"error": response.text}

    job_id = response.json().get("id")

    # Step 2: Poll until done
    while True:
        check = requests.get(f"{AI_HORDE_CHECK}{job_id}", headers=HEADERS)
        data = check.json()

        if data.get("done"):
            break

        time.sleep(2)

    if not data.get("generations"):
        return {"error": "Image generation failed"}

    image_url = data["generations"][0]["img"]

    # Step 3: Download image
    image_data = requests.get(image_url).content

    os.makedirs("generated_images", exist_ok=True)
    filename = f"{uuid.uuid4()}.png"
    relative_path = os.path.join("generated_images", filename)


    with open(relative_path, "wb") as f:
        f.write(image_data)

    return {"image_path": relative_path.replace("\\", "/")}