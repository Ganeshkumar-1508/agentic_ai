from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Force NVIDIA provider
os.environ["LITELLM_PROVIDER"] = "nvidia"
os.environ["LITELLM_MODEL"] = os.getenv("LITELLM_MODEL")
os.environ["LITELLM_BASE_URL"] = os.getenv("LITELLM_BASE_URL")
os.environ["NVIDIA_API_KEY"] = os.getenv("NVIDIA_API_KEY")

# Debug print
print("✅ PROVIDER =", os.environ.get("LITELLM_PROVIDER"))
print("✅ MODEL =", os.environ.get("LITELLM_MODEL"))
print("✅ KEY PRESENT =", bool(os.environ.get("NVIDIA_API_KEY")))
