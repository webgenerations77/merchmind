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
# A light, near-neutral pixel is treated as background (gradient / vignette /
# off-white) even if it's not pure white. Saturation (max-min channel spread)
# stays low for grays but is high for colored artwork, so coloured/dark art
# is preserved while grey corner gradients get stripped.
_GRAY_BG_MIN = 200       # minimum channel brightness to count as "light"
_GRAY_NEUTRAL_TOL = 22   # max channel spread to count as "near-neutral grey"


def remove_white_background(image_bytes: bytes, threshold: int = _WHITE_THRESHOLD) -> bytes:
    """Convert near-white and light near-neutral-grey pixels to transparent.

    The pure-white pass handles clean backgrounds; the neutral-grey pass catches
    the soft grey gradients/vignettes Flux sometimes leaves in the corners that a
    flat white threshold misses. Coloured and dark artwork is left untouched.
    Returns PNG bytes.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            if r > threshold and g > threshold and b > threshold:
                new_data.append((r, g, b, 0))
            elif min(r, g, b) > _GRAY_BG_MIN and (max(r, g, b) - min(r, g, b)) < _GRAY_NEUTRAL_TOL:
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
