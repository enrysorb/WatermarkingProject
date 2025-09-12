from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

def apply_visible_watermark(image_bytes: bytes, text: str, position: str = "bottom-right", opacity: float = 0.5, size: int = 20) -> bytes:
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    watermark = Image.new("RGBA", img.size)
    draw = ImageDraw.Draw(watermark)
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size)
            except (OSError, IOError):
                font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    margin = 10

    if position == "top-left":
        pos = (margin, margin)
    elif position == "top-right":
        pos = (img.width - text_width - margin, margin)
    elif position == "bottom-left":
        pos = (margin, img.height - text_height - margin)
    elif position == "bottom-right":
        pos = (img.width - text_width - margin, img.height - text_height - margin)
    elif position == "center":
        pos = (
            (img.width - text_width) // 2,
            (img.height - text_height) // 2
        )
    else:
        pos = (margin, margin)

    alpha = int(opacity * 255)
    alpha = max(0, min(255, alpha))  

    draw.text(pos, text, font=font, fill=(255, 255, 255, alpha))  

    combined = Image.alpha_composite(img, watermark)
    output = BytesIO()
    combined.convert("RGB").save(output, format="PNG")
    return output.getvalue()