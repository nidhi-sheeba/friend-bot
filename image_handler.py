# image_handler.py
import os
import base64
import tempfile
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def interpret_image(file, caption: str = "", tone_prompt: str = "") -> str:
    """
    Downloads a Telegram photo, converts to base64,
    sends to Claude vision, returns interpretation.
    """
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    await file.download_to_drive(tmp_path)

    try:
        # Read and encode to base64
        with open(tmp_path, "rb") as img_file:
            image_data = base64.standard_b64encode(img_file.read()).decode("utf-8")

        # Build the prompt
        user_text = caption if caption else "What do you see in this image? Describe and interpret it."

        # Call Claude with vision
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=tone_prompt,  # apply the user's chosen tone
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": user_text
                        }
                    ],
                }
            ],
        )

        return response.content[0].text

    finally:
        os.unlink(tmp_path)