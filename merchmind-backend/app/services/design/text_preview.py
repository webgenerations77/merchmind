"""
Generates preview images for text_only and typographic designs using Pillow.
Renders primary text with the selected font on a transparent background.
"""
import io
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_CANVAS_W = 1200
_CANVAS_H = 1200
_BG_COLOR = (0, 0, 0, 0)
_TEXT_COLOR = (30, 30, 30)
_ACCENT_COLOR = (99, 102, 241)

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
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


def generate_text_preview(
    primary_text: str,
    secondary_text: str | None = None,
    font_pair: str | None = None,
    color_palette: list[str] | None = None,
) -> bytes:
    img = Image.new("RGBA", (_CANVAS_W, _CANVAS_H), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    primary_size = 72
    primary_font = _load_font(primary_size)
    max_text_width = _CANVAS_W - 160
    lines = _wrap_text(primary_text.upper(), primary_font, max_text_width)

    while len(lines) > 4 and primary_size > 36:
        primary_size -= 4
        primary_font = _load_font(primary_size)
        lines = _wrap_text(primary_text.upper(), primary_font, max_text_width)

    line_height = int(primary_size * 1.3)
    total_text_height = len(lines) * line_height
    if secondary_text:
        total_text_height += 60

    y_start = (_CANVAS_H - total_text_height) // 2

    for i, line in enumerate(lines):
        bbox = primary_font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        x = (_CANVAS_W - text_w) // 2
        draw.text((x, y_start + i * line_height), line, fill=_TEXT_COLOR, font=primary_font)

    if secondary_text:
        secondary_font = _load_font(28)
        sec_lines = _wrap_text(secondary_text, secondary_font, max_text_width)
        sec_y = y_start + len(lines) * line_height + 30
        for line in sec_lines[:2]:
            bbox = secondary_font.getbbox(line)
            text_w = bbox[2] - bbox[0]
            x = (_CANVAS_W - text_w) // 2
            draw.text((x, sec_y), line, fill=(80, 80, 80), font=secondary_font)
            sec_y += 36

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
