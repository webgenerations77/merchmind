"""
Generate product mockup composites using Pillow.
For product types where Printify doesn't return mockup images,
we create our own by overlaying the design onto a product template.
"""
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "tshirt": {
        "size": (800, 1000),
        "bg_color": (30, 30, 30),
        "design_area": (200, 200, 600, 600),
        "design_area_text": (200, 140, 600, 480),
        "label": "T-Shirt",
    },
    "mug": {
        "size": (800, 600),
        "bg_color": (245, 245, 245),
        "design_area": (175, 100, 625, 450),
        "label": "Mug",
    },
    "sticker": {
        "size": (600, 600),
        "bg_color": (240, 240, 240),
        "design_area": (50, 50, 550, 550),
        "label": "Sticker",
    },
    "phone_case": {
        "size": (500, 900),
        "bg_color": (30, 30, 30),
        "design_area": (65, 100, 435, 780),
        "corner_radius": 40,
        "label": "Phone Case",
    },
}

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _load_font(size: int):
    for path in _FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _smart_crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop an image to match the target aspect ratio, then resize."""
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if abs(src_ratio - target_ratio) < 0.05:
        return img.resize((target_w, target_h), Image.LANCZOS)

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def generate_mockup(product_type: str, design_bytes: bytes, archetype: str | None = None) -> bytes | None:
    """Generate a mockup composite for a product type. Returns PNG bytes or None."""
    template = _TEMPLATES.get(product_type)
    if not template:
        return None

    try:
        canvas = Image.new("RGB", template["size"], template["bg_color"])
        draw = ImageDraw.Draw(canvas)

        design = Image.open(io.BytesIO(design_bytes)).convert("RGBA")

        is_text_design = archetype in ("text_only", "typographic", "text_icon")
        if is_text_design and "design_area_text" in template:
            area = template["design_area_text"]
        else:
            area = template["design_area"]
        area_w = area[2] - area[0]
        area_h = area[3] - area[1]
        design_resized = _smart_crop_to_aspect(design, area_w, area_h)

        canvas.paste(design_resized, (area[0], area[1]), design_resized)

        if product_type == "tshirt":
            collar_color = (50, 50, 50)
            draw.arc([300, 15, 500, 120], start=200, end=340, fill=collar_color, width=3)
            draw.line([(200, 200), (100, 300), (100, 400), (200, 350)], fill=collar_color, width=2)
            draw.line([(600, 200), (700, 300), (700, 400), (600, 350)], fill=collar_color, width=2)
            draw.rounded_rectangle([150, 180, 650, 900], radius=20, outline=collar_color, width=2)

        elif product_type == "mug":
            mug_color = (200, 200, 200)
            draw.rounded_rectangle([120, 60, 680, 500], radius=30, outline=mug_color, width=3)
            draw.arc([650, 150, 770, 400], start=270, end=90, fill=mug_color, width=3)
            draw.line([(120, 500), (680, 500)], fill=mug_color, width=3)

        elif product_type == "sticker":
            outline_color = (200, 200, 200)
            draw.rounded_rectangle([area[0] - 8, area[1] - 8, area[2] + 8, area[3] + 8], radius=20, outline=outline_color, width=2)

        elif product_type == "phone_case":
            outline_color = (80, 80, 80)
            draw.rounded_rectangle([50, 60, 450, 840], radius=40, outline=outline_color, width=3)
            draw.rounded_rectangle([60, 70, 440, 830], radius=36, outline=(50, 50, 50), width=1)
            draw.ellipse([215, 850, 285, 870], outline=outline_color, width=2)

        label_font = _load_font(16)
        label = template.get("label", product_type)
        lw = label_font.getbbox(label)[2]
        draw.text((template["size"][0] - lw - 15, template["size"][1] - 30), label, fill=(150, 150, 150), font=label_font)

        buf = io.BytesIO()
        canvas.save(buf, format="PNG", quality=95)
        return buf.getvalue()

    except Exception as e:
        logger.warning("Mockup generation failed for %s: %s", product_type, e)
        return None


def generate_all_missing_mockups(design_image_bytes: bytes, product_types: list[str]) -> dict[str, bytes]:
    """Generate mockup composites for product types that Printify doesn't cover."""
    results = {}
    for pt in product_types:
        if pt in _TEMPLATES:
            mockup_bytes = generate_mockup(pt, design_image_bytes)
            if mockup_bytes:
                results[pt] = mockup_bytes
    return results
