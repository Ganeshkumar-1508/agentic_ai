from crewai.tools import BaseTool
from services.image_service import generate_image


class ImageGenerationTool(BaseTool):

    name: str = "Image Generator"
    description: str = "Generate an image using AI Horde API"

    def _run(self, prompt: str):
        result = generate_image(prompt)

        # If service returns dict, extract clean path
        if isinstance(result, dict) and "image_path" in result:
            return result["image_path"]

        # If already string, return as is
        if isinstance(result, str):
            return result

        # Fallback safety
        return "IMAGE_GENERATION_FAILED"