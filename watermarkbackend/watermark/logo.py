from PIL import Image, ImageDraw
from io import BytesIO

def apply_logo_watermark(image_bytes: bytes, logo_bytes: bytes, position: str = "bottom-right", opacity: float = 0.7, size: float = 0.1) -> bytes:
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    
    logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
    
    logo_width = int(img.width * size)
    logo_height = int(logo.height * (logo_width / logo.width))
    
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
  
    if opacity < 1.0:
        alpha = logo.split()[-1]  
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)

    margin = 20
    
    positions = {
        "top-left": (margin, margin),
        "top-right": (img.width - logo_width - margin, margin),
        "bottom-left": (margin, img.height - logo_height - margin),
        "bottom-right": (img.width - logo_width - margin, img.height - logo_height - margin),
        "center": ((img.width - logo_width) // 2, (img.height - logo_height) // 2)
    }
    
    pos = positions.get(position, positions["bottom-right"])

    img.paste(logo, pos, logo)

    output = BytesIO()
    img.convert("RGB").save(output, format="PNG")
    return output.getvalue()