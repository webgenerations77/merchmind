"""
Generates preview images for text_only and typographic designs using Pillow.

DESIGN TYPE AUDIT (Section 1):
  Archetypes handled: text_only, typographic (select_image_api returns None)
  No image generation API called — pure Pillow rendering
  Two variants per design: dark (white text) and light (dark text + outline)
  Product types select the appropriate variant at Printify creation time
  Font: uses Claude-selected font_pair with fallback to DejaVu Serif Bold
  Canvas: 4500x5400 transparent RGBA
  Font size: dynamically calculated as % of canvas width based on word count
"""
import io
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_CANVAS_W = 4500
_CANVAS_H = 5400
_BG_COLOR = (0, 0, 0, 0)

_LIGHT_PRODUCT_TYPES = {"mug", "sticker", "phone_case", "poster"}
_DARK_PRODUCT_TYPES = {"tshirt", "hoodie", "long_sleeve", "hat"}

_FONTS_DIR = Path(__file__).parent.parent.parent / "fonts"

_FONT_FILE_NAMES = {
    "Bebas Neue": "BebasNeue-Regular.ttf",
    "Oswald": ("Oswald-Bold.ttf", "Oswald-Regular.ttf"),
    "Nunito": ("Nunito-Bold.ttf", "Nunito-Regular.ttf"),
    "Playfair Display": ("PlayfairDisplay-Bold.ttf", "PlayfairDisplay-Regular.ttf"),
    "Anton": "Anton-Regular.ttf",
    "Montserrat": ("Montserrat-Bold.ttf", "Montserrat-Regular.ttf"),
    "Pacifico": "Pacifico-Regular.ttf",
    "Roboto Condensed": ("RobotoCondensed-Bold.ttf", "RobotoCondensed-Regular.ttf"),
    "Impact": "impact.ttf",
    "Raleway": ("Raleway-Bold.ttf", "Raleway-Regular.ttf"),
    "Permanent Marker": "PermanentMarker-Regular.ttf",
    "Abril Fatface": "AbrilFatface-Regular.ttf",
}

_FALLBACK_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_FALLBACK_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _find_font_file(font_name: str) -> str | None:
    """Search for a TTF matching the font name in project fonts/ and system dirs."""
    if not font_name:
        return None

    entry = _FONT_FILE_NAMES.get(font_name)
    if entry:
        candidates = [entry] if isinstance(entry, str) else list(entry)
    else:
        slug = font_name.replace(" ", "")
        candidates = [f"{slug}-Bold.ttf", f"{slug}.ttf", f"{slug}-Regular.ttf"]

    search_dirs = []
    if _FONTS_DIR.exists():
        search_dirs.append(_FONTS_DIR)
    search_dirs.extend([
        Path("/usr/share/fonts/truetype"),
        Path("C:/Windows/Fonts"),
    ])

    for d in search_dirs:
        if not d.exists():
            continue
        for c in candidates:
            p = d / c
            if p.exists():
                return str(p)
            if d.is_dir():
                for sub in d.iterdir():
                    if sub.is_dir():
                        p2 = sub / c
                        if p2.exists():
                            return str(p2)
    return None


def _load_font(size: int, font_name: str | None = None, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_name:
        path = _find_font_file(font_name)
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    fallbacks = _FALLBACK_BOLD if bold else _FALLBACK_REGULAR
    for path in fallbacks:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _parse_font_pair(font_pair: str | None) -> tuple[str | None, str | None]:
    if not font_pair:
        return None, None
    parts = [p.strip() for p in font_pair.split("/")]
    primary = parts[0] if parts else None
    secondary = parts[1] if len(parts) > 1 else None
    return primary, secondary


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


def _measure_widest_line(lines: list[str], font) -> int:
    widest = 0
    for line in lines:
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        if w > widest:
            widest = w
    return widest


def _fill_targets(word_count: int) -> tuple[float, float]:
    """(min_fill, max_fill) as fractions of canvas width."""
    if word_count <= 3:
        return 0.65, 0.80
    elif word_count <= 7:
        return 0.55, 0.70
    else:
        return 0.45, 0.60


def _fit_font_size(
    text: str,
    font_name: str | None,
    canvas_w: int,
    canvas_h: int,
    word_count: int,
) -> tuple[int, list[str], ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    """Binary search for the largest font size that fits within the target fill zone."""
    _min_fill, max_fill = _fill_targets(word_count)
    wrap_width = int(canvas_w * max_fill)
    max_height = int(canvas_h * 0.70)

    lo, hi = 60, min(int(canvas_w * 0.7), int(canvas_h * 0.45))

    for _ in range(25):
        mid = (lo + hi) // 2
        if mid <= lo:
            break
        font = _load_font(mid, font_name, bold=True)
        lines = _wrap_text(text, font, wrap_width)
        widest = _measure_widest_line(lines, font)
        total_h = len(lines) * int(mid * 1.35)

        if total_h > max_height or widest > wrap_width:
            hi = mid
        else:
            lo = mid

    font = _load_font(lo, font_name, bold=True)
    lines = _wrap_text(text, font, wrap_width)
    return lo, lines, font


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font,
    fill: tuple,
    outline_color: tuple | None = None,
    outline_width: int = 3,
):
    if outline_color:
        x, y = pos
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    draw.text(pos, text, fill=fill, font=font)


def generate_text_preview(
    primary_text: str,
    secondary_text: str | None = None,
    font_pair: str | None = None,
    color_palette: list[str] | None = None,
    dark_mode: bool = True,
    position: str = "center",
    alignment: str = "center",
) -> bytes:
    """Render text design on a 4500x5400 transparent canvas.

    dark_mode=True: white text (tshirt, hoodie, hat, long_sleeve)
    dark_mode=False: near-black text with white outline (mug, phone_case, sticker, poster)
    """
    primary_font_name, secondary_font_name = _parse_font_pair(font_pair)

    if dark_mode:
        text_color = (255, 255, 255)
        secondary_color = (200, 200, 200)
        outline_color = None
        outline_w = 0
    else:
        text_color = (26, 26, 26)
        secondary_color = (80, 80, 80)
        outline_color = (255, 255, 255)
        outline_w = 3

    img = Image.new("RGBA", (_CANVAS_W, _CANVAS_H), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    display_text = primary_text.upper()
    word_count = len(primary_text.split())

    primary_size, lines, primary_font = _fit_font_size(
        display_text, primary_font_name, _CANVAS_W, _CANVAS_H, word_count,
    )

    line_height_factor = 1.4 if word_count > 7 else 1.3
    line_height = int(primary_size * line_height_factor)
    primary_block_h = len(lines) * line_height

    sec_lines = []
    secondary_font = None
    sec_line_height = 0
    if secondary_text:
        sec_size = max(40, primary_size // 3)
        secondary_font = _load_font(sec_size, secondary_font_name, bold=False)
        sec_lines = _wrap_text(secondary_text, secondary_font, int(_CANVAS_W * 0.70))[:2]
        sec_line_height = int(sec_size * 1.3)

    sec_block_h = len(sec_lines) * sec_line_height
    gap = int(primary_size * 0.5) if sec_lines else 0
    total_h = primary_block_h + gap + sec_block_h

    if position == "upper":
        y_start = _CANVAS_H // 6
    else:
        y_start = (_CANVAS_H - total_h) // 2

    fill_ratio = 0.0
    for i, line in enumerate(lines):
        bbox = primary_font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        line_fill = text_w / _CANVAS_W
        if line_fill > fill_ratio:
            fill_ratio = line_fill

        if alignment == "left":
            x = int(_CANVAS_W * 0.10)
        else:
            x = (_CANVAS_W - text_w) // 2

        _draw_outlined_text(
            draw, (x, y_start + i * line_height), line,
            primary_font, text_color, outline_color, outline_w,
        )

    if sec_lines and secondary_font:
        sec_y = y_start + primary_block_h + gap
        for line in sec_lines:
            bbox = secondary_font.getbbox(line)
            text_w = bbox[2] - bbox[0]
            if alignment == "left":
                x = int(_CANVAS_W * 0.10)
            else:
                x = (_CANVAS_W - text_w) // 2
            _draw_outlined_text(
                draw, (x, sec_y), line,
                secondary_font, secondary_color, outline_color, max(1, outline_w - 1),
            )
            sec_y += sec_line_height

    logger.info(
        "text_preview: size=%dx%d font_size=%dpx fill_ratio=%.2f words=%d lines=%d "
        "font='%s' dark=%s",
        _CANVAS_W, _CANVAS_H, primary_size, fill_ratio, word_count, len(lines),
        primary_font_name or "fallback-serif", dark_mode,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
