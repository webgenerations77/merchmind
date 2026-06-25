"""
Composites text slogans onto AI-generated design images.
Used for hybrid and text_icon archetypes that pair an image with a phrase.

DESIGN TYPE AUDIT (Section 1):
  Archetypes handled: hybrid, text_icon (via should_composite check)
  NOT touched in this session — image+text path is a separate session.
  Inputs: image bytes + primary/secondary text + archetype + color palette
  Output: composited PNG with gradient band + outlined text in lower portion
"""
import io
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FONT_PATHS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_FONT_PATHS_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

_COMPOSITE_ARCHETYPES = {"hybrid", "text_icon"}


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = _FONT_PATHS_BOLD if bold else _FONT_PATHS_REGULAR
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _region_luminance(img: Image.Image, y_start: int, y_end: int) -> float:
    """Average luminance of a horizontal band of the image."""
    region = img.crop((0, y_start, img.width, y_end)).convert("RGB")
    small = region.resize((64, 16), Image.LANCZOS)
    pixels = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    if not pixels:
        return 0.0
    total = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels)
    return total / len(pixels)


def _pick_text_color(img: Image.Image, y_start: int, y_end: int) -> tuple:
    """White text on dark regions, dark text on light regions."""
    lum = _region_luminance(img, y_start, y_end)
    if lum > 140:
        return (20, 20, 20, 255)
    return (255, 255, 255, 255)


def _draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font,
    fill: tuple,
    outline_color: tuple = (0, 0, 0, 180),
    outline_width: int = 2,
):
    """Draw text with an outline for readability on any background."""
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    draw.text(pos, text, fill=fill, font=font)


def should_composite(archetype: str) -> bool:
    return archetype in _COMPOSITE_ARCHETYPES


def composite_text_on_image(
    image_bytes: bytes,
    primary_text: str,
    secondary_text: str | None = None,
    archetype: str = "hybrid",
    color_palette: list[str] | None = None,
) -> bytes:
    """
    Overlay text onto a design image.
    Places primary text in the lower portion with an outline for contrast.
    Returns composited PNG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    max_text_width = int(w * 0.85)
    margin_bottom = int(h * 0.06)

    primary_size = max(36, min(72, w // 12))
    primary_font = _load_font(primary_size, bold=True)
    lines = _wrap_text(primary_text.upper(), primary_font, max_text_width)

    while len(lines) > 3 and primary_size > 36:
        primary_size -= 4
        primary_font = _load_font(primary_size, bold=True)
        lines = _wrap_text(primary_text.upper(), primary_font, max_text_width)

    line_height = int(primary_size * 1.35)
    primary_block_height = len(lines) * line_height

    sec_lines = []
    secondary_font = None
    sec_line_height = 0
    if secondary_text:
        sec_size = max(20, primary_size // 2)
        secondary_font = _load_font(sec_size, bold=False)
        sec_lines = _wrap_text(secondary_text, secondary_font, max_text_width)[:2]
        sec_line_height = int(sec_size * 1.3)

    sec_block_height = len(sec_lines) * sec_line_height
    gap = int(primary_size * 0.4) if sec_lines else 0
    total_text_height = primary_block_height + gap + sec_block_height

    text_top = h - margin_bottom - total_text_height

    # Gradient band behind text for readability
    grad_top = max(0, text_top - int(h * 0.05))
    grad_bottom = h
    for y in range(grad_top, grad_bottom):
        progress = (y - grad_top) / max(1, grad_bottom - grad_top)
        alpha = int(140 * progress)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    text_color = _pick_text_color(img, text_top, min(h, text_top + total_text_height))
    outline_width = max(1, primary_size // 24)

    y_cursor = text_top
    for line in lines:
        bbox = primary_font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        _draw_text_with_outline(draw, (x, y_cursor), line, primary_font, text_color, outline_width=outline_width)
        y_cursor += line_height

    if sec_lines and secondary_font:
        y_cursor += gap
        sec_color = (*text_color[:3], 220)
        for line in sec_lines:
            bbox = secondary_font.getbbox(line)
            text_w = bbox[2] - bbox[0]
            x = (w - text_w) // 2
            _draw_text_with_outline(draw, (x, y_cursor), line, secondary_font, sec_color, outline_width=max(1, outline_width - 1))
            y_cursor += sec_line_height

    result = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
