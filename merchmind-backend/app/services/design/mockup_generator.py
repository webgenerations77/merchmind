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
        "label": "T-Shirt",
    },
    "mug": {
        "size": (800, 600),
        "bg_color": (245, 245, 245),
        "design_area": (175, 100, 625, 450),
        "label": "Mug",
    },
    "poster": {
        "size": (800, 1000),
        "bg_color": (245, 242, 237),
        "design_area": (80, 120, 640, 760),
        "frame_color": (60, 60, 60),
        "frame_width": 4,
        "label": "Poster",
    },
    "phone_case": {
        "size": (500, 900),
        "bg_color": (30, 30, 30),
        "design_area": (75, 180, 350, 550),
        "corner_radius": 40,
        "label": "Phone Case",
    },
    "sticker": {
        "size": (600, 600),
        "bg_color": (255, 255, 255),
        "design_area": (75, 75, 450, 450),
        "label": "Sticker",
        "border_color": (200, 200, 200),
        "border_dash": True,
    },
    "hat": {
        "size": (800, 600),
        "bg_color": (40, 40, 40),
        "design_area": (225, 100, 350, 250),
        "label": "Hat",
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


def generate_mockup(product_type: str, design_bytes: bytes) -> bytes | None:
    """Generate a mockup composite for a product type. Returns PNG bytes or None."""
    template = _TEMPLATES.get(product_type)
    if not template:
        return None

    try:
        canvas = Image.new("RGB", template["size"], template["bg_color"])
        draw = ImageDraw.Draw(canvas)

        design = Image.open(io.BytesIO(design_bytes)).convert("RGBA")

        area = template["design_area"]
        area_w = area[2] - area[0]
        area_h = area[3] - area[1]
        design_resized = design.resize((area_w, area_h), Image.LANCZOS)

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

        elif product_type == "poster":
            fc = template["frame_color"]
            fw = template["frame_width"]
            draw.rectangle([area[0] - fw, area[1] - fw, area[2] + fw, area[3] + fw], outline=fc, width=fw)
            shadow_color = (220, 218, 213)
            draw.rectangle([area[0] + 4, area[3] + fw, area[2] + fw + 4, area[3] + fw + 20], fill=shadow_color)

        elif product_type == "phone_case":
            outline_color = (80, 80, 80)
            draw.rounded_rectangle([50, 60, 450, 840], radius=40, outline=outline_color, width=3)
            draw.rounded_rectangle([60, 70, 440, 830], radius=36, outline=(50, 50, 50), width=1)
            draw.ellipse([215, 850, 285, 870], outline=outline_color, width=2)

        elif product_type == "sticker":
            bc = template.get("border_color", (200, 200, 200))
            draw.rounded_rectangle([50, 50, 550, 550], radius=20, outline=bc, width=2)
            label_font = _load_font(14)
            draw.text((250, 565), "Sticker · Die Cut", fill=(150, 150, 150), font=label_font, anchor="mt")

        elif product_type == "hat":
            draw.arc([100, 50, 700, 500], start=200, end=340, fill=(60, 60, 60), width=3)
            draw.rounded_rectangle([150, 350, 650, 550], radius=10, outline=(60, 60, 60), width=2)
            label_font = _load_font(14)
            draw.text((400, 560), "Embroidered Hat", fill=(150, 150, 150), font=label_font, anchor="mt")

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
