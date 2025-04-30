import openai
import base64
from io import BytesIO
from typing import Tuple
from PIL import Image

# === Encode image to base64 for GPT-4o ===
def encode_image_to_base64(img: Image.Image) -> str:
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


# === GPT-4o: Analyze image + return a DALL·E prompt ===
def generate_banner_prompt_gpt4(image: Image.Image, prompt_text: str) -> str:
    img_base64 = encode_image_to_base64(image)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    { "type": "text", "text": prompt_text },
                    { "type": "image_url",
                      "image_url": {
                          "url": f"data:image/jpeg;base64,{img_base64}",
                          "detail": "high"
                      }
                    }
                ]
            }
        ],
        temperature=0.5,
    )

    return response.choices[0].message.content.strip()


# === DALL·E: Select best native output size based on aspect ratio ===
def get_best_dalle_size(aspect_ratio: float) -> str:
    """
    Maps an arbitrary aspect ratio to the closest supported DALL·E 3 size.
    """
    size_options = {
        "square": (1.0, "1024x1024"),
        "wide": (1792 / 1024, "1792x1024"),
        "tall": (1024 / 1792, "1024x1792"),
    }

    closest = min(size_options.values(), key=lambda x: abs(x[0] - aspect_ratio))
    return closest[1]


# === DALL·E: Generate the image ===
def generate_dalle_image(prompt: str, aspect_ratio: Tuple[int, int]) -> str:
    # berechne Format
    width, height = aspect_ratio
    if width / height >= 1.7:
        size = "1792x1024"
    elif width / height > 1.3:
        size = "1536x1024"
    elif width / height == 1:
        size = "1024x1024"
    else:
        size = "1024x1536"

    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        n=1,
        response_format="url"
    )
    return response.data[0].url

