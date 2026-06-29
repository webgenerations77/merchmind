"""
Post-processing pipeline for generated images using Pillow + rembg.
Steps: background removal → normalize canvas → contrast check →
bleed zone check → color palette extraction → Supabase upload.
"""
import io
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from PIL import Image
from rembg import remove

from app.utils.exceptions import PostProcessingError, ContrastCheckFailedError, BleedZoneViolationError, StorageUploadError
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_CANVAS_WIDTH = 4500
_CANVAS_HEIGHT = 5400
_BLEED_MARGIN = 200
_MIN_CONTRAST_RATIO = 4.5


@dataclass
class ProcessedDesign:
    design_id: str
    processed_url: str
    color_palette: list[str]
    contrast: dict
    bleed: dict
    warnings: list[str] = field(default_factory=list)


def _relative_luminance(r: int, g: int, b: int) -> float:
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast_ratio(l1: float, l2: float) -> float:
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _harden_alpha(img: Image.Image, low: int = 50) -> Image.Image:
    """Zero out faint semi-transparent pixels so rembg's ghost halos/smudges
    (the orange/grey blotches it leaves around a subject) become fully
    transparent and won't print. Edge anti-aliasing (alpha >= low) is preserved.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < low else p)
    img.putalpha(a)
    return img


def remove_background(image_bytes: bytes) -> Image.Image:
    # post_process_mask=True drops stray mask islands rembg would otherwise keep;
    # _harden_alpha then clears the faint semi-transparent halo it leaves behind.
    result = remove(image_bytes, post_process_mask=True)
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    return _harden_alpha(img)


def _autocrop(img: Image.Image, threshold: int = 10) -> Image.Image:
    """Crop to content bounds by trimming transparent/near-transparent edges."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.split()[3]
    bbox = alpha.point(lambda p: 255 if p > threshold else 0).getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def normalize_canvas(img: Image.Image) -> Image.Image:
    img = _autocrop(img)

    canvas = Image.new("RGBA", (_CANVAS_WIDTH, _CANVAS_HEIGHT), (0, 0, 0, 0))
    max_w = _CANVAS_WIDTH - (_BLEED_MARGIN * 2)
    max_h = _CANVAS_HEIGHT - (_BLEED_MARGIN * 2)

    scale = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    x = (_CANVAS_WIDTH - new_w) // 2
    y = (_CANVAS_HEIGHT - new_h) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def check_contrast(img: Image.Image) -> dict:
    white_bg = Image.new("RGB", img.size, (255, 255, 255))
    white_bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
    cx, cy = img.width // 2, img.height // 2
    sample_size = min(100, img.width // 4)
    region = white_bg.crop((cx - sample_size, cy - sample_size, cx + sample_size, cy + sample_size))
    pixels = list(region.getdata())
    colored = [(r, g, b) for r, g, b in pixels if (r, g, b) != (255, 255, 255)]
    avg = tuple(int(sum(c[i] for c in colored) / len(colored)) for i in range(3)) if colored else (128, 128, 128)
    design_lum = _relative_luminance(*avg)
    white_ratio = _contrast_ratio(design_lum, _relative_luminance(255, 255, 255))
    black_ratio = _contrast_ratio(design_lum, _relative_luminance(0, 0, 0))
    return {
        "white_ok": white_ratio >= _MIN_CONTRAST_RATIO,
        "black_ok": black_ratio >= _MIN_CONTRAST_RATIO,
        "white_ratio": round(white_ratio, 2),
        "black_ratio": round(black_ratio, 2),
    }


def check_bleed_zone(img: Image.Image) -> dict:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    flagged = []
    alpha = img.split()[3]
    pixels = alpha.load()
    w, h = img.size

    def has_content(x_range, y_range):
        return any(pixels[x, y] > 10 for x in x_range for y in y_range)

    if has_content(range(w), range(_BLEED_MARGIN)):
        flagged.append("top")
    if has_content(range(w), range(h - _BLEED_MARGIN, h)):
        flagged.append("bottom")
    if has_content(range(_BLEED_MARGIN), range(h)):
        flagged.append("left")
    if has_content(range(w - _BLEED_MARGIN, w), range(h)):
        flagged.append("right")

    return {"bleed_ok": len(flagged) == 0, "flagged_edges": flagged}


def extract_color_palette(img: Image.Image, num_colors: int = 4) -> list[str]:
    rgb_img = img.convert("RGB")
    small = rgb_img.resize((150, 150), Image.LANCZOS)
    quantized = small.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    colors = []
    for i in range(num_colors):
        r, g, b = palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2]
        if (r, g, b) == (255, 255, 255):
            continue
        colors.append(f"#{r:02x}{g:02x}{b:02x}")
    return colors[:num_colors]


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def process_image(raw_bytes: bytes) -> tuple[Image.Image, dict]:
    """Full pipeline without Supabase upload. Returns (image, report)."""
    img_nobg = remove_background(raw_bytes)
    canvas = normalize_canvas(img_nobg)
    contrast = check_contrast(canvas)
    bleed = check_bleed_zone(canvas)
    palette = extract_color_palette(canvas)

    warnings = []
    if not contrast["white_ok"]:
        warnings.append(f"Low contrast on white background ({contrast['white_ratio']}:1)")
    if not contrast["black_ok"]:
        warnings.append(f"Low contrast on black background ({contrast['black_ratio']}:1)")
    if not bleed["bleed_ok"]:
        warnings.append(f"Content in bleed zone: {bleed['flagged_edges']}")

    return canvas, {
        "contrast": contrast,
        "bleed": bleed,
        "color_palette": palette,
        "warnings": warnings,
    }


def process_and_upload(raw_bytes: bytes, design_id: str) -> ProcessedDesign:
    """
    Full pipeline: process image then upload processed PNG to Supabase.
    Returns ProcessedDesign with the public URL.
    """
    try:
        canvas, report = process_image(raw_bytes)
    except Exception as e:
        raise PostProcessingError(f"Image processing failed for design {design_id}: {e}") from e

    processed_bytes = image_to_bytes(canvas)
    path = storage.design_processed_path(design_id)

    try:
        url = storage.upload(path, processed_bytes, "image/png")
    except Exception as e:
        raise StorageUploadError(f"Failed to upload processed image for design {design_id}: {e}") from e

    logger.info("post_processor.process_and_upload design_id=%s url=%s warnings=%d", design_id, url, len(report["warnings"]))

    return ProcessedDesign(
        design_id=design_id,
        processed_url=url,
        color_palette=report["color_palette"],
        contrast=report["contrast"],
        bleed=report["bleed"],
        warnings=report["warnings"],
    )
