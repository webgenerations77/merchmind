"""
Lightweight background removal using Pillow.
Converts near-white pixels to transparent. No neural network needed.
Works well with Flux Schnell images that already have white backgrounds.
"""
import io
from PIL import Image
import logging

logger = logging.getLogger(__name__)

_WHITE_THRESHOLD = 235


def remove_white_background(image_bytes: bytes, threshold: int = _WHITE_THRESHOLD) -> bytes:
    """Convert near-white pixels to transparent. Returns PNG bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            if r > threshold and g > threshold and b > threshold:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning("White bg removal failed, returning original: %s", e)
        return image_bytes
