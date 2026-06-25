"""
Generate product mockup composites using Pillow.
For product types where Printify doesn't return mockup images,
we create our own by overlaying the design onto a product template.
"""
import io
import logging
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "tshirt": {
        "size": (800, 1000),
        "bg_color": (255, 255, 255),
        "design_area": (200, 200, 600, 600),
        "design_area_text": (200, 140, 600, 480),
        "label": "T-Shirt",
    },
    "hoodie": {
        "size": (800, 1000),
        "bg_color": (255, 255, 255),
        "design_area": (210, 250, 590, 580),
        "design_area_text": (210, 190, 590, 480),
        "label": "Hoodie",
    },
    "long_sleeve": {
        "size": (800, 1000),
        "bg_color": (255, 255, 255),
        "design_area": (200, 200, 600, 600),
        "design_area_text": (200, 140, 600, 480),
        "label": "Long Sleeve",
    },
    "mug": {
        "size": (900, 700),
        "bg_color": (255, 255, 255),
        "design_area": (200, 130, 620, 440),
        "label": "Mug",
    },
    "sticker": {
        "size": (700, 700),
        "bg_color": (245, 245, 245),
        "design_area": (100, 100, 600, 600),
        "label": "Sticker",
    },
    "phone_case": {
        "size": (550, 1000),
        "bg_color": (255, 255, 255),
        "design_area": (80, 120, 470, 780),
        "corner_radius": 40,
        "label": "Phone Case",
    },
    "hat": {
        "size": (800, 700),
        "bg_color": (255, 255, 255),
        "design_area": (250, 160, 550, 380),
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


def _add_drop_shadow(canvas: Image.Image, shape_bbox: tuple, radius: int = 15, offset: tuple = (4, 6), color: tuple = (0, 0, 0, 60)):
    """Add a soft drop shadow behind a rectangular region."""
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = shape_bbox
    sd.rounded_rectangle(
        [x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]],
        radius=radius, fill=color,
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    canvas.paste(Image.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 0)), shadow), mask=shadow)


def _draw_mug(canvas: Image.Image, draw: ImageDraw.Draw, design: Image.Image, area: tuple):
    """Draw a realistic mug with handle, surface shading, and design."""
    mug_body = (130, 90, 670, 530)
    mug_color = (255, 255, 255)
    handle_color = (230, 230, 230)
    rim_color = (210, 210, 210)

    _add_drop_shadow(canvas, mug_body, radius=30, offset=(6, 8), color=(0, 0, 0, 50))

    draw.rounded_rectangle(mug_body, radius=12, fill=mug_color)

    draw.arc([650, 180, 790, 430], start=270, end=90, fill=handle_color, width=18)
    draw.arc([655, 185, 785, 425], start=270, end=90, fill=(245, 245, 245), width=8)

    draw.line([(130, 90), (670, 90)], fill=rim_color, width=6)
    draw.rounded_rectangle([130, 510, 670, 540], radius=6, fill=(235, 235, 235))

    area_w = area[2] - area[0]
    area_h = area[3] - area[1]
    design_resized = _smart_crop_to_aspect(design, area_w, area_h)
    canvas.paste(design_resized, (area[0], area[1]), design_resized)

    shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    for i in range(30):
        alpha = int(15 * (1 - i / 30))
        shade_draw.line([(130 + i, 90), (130 + i, 530)], fill=(0, 0, 0, alpha))
    for i in range(30):
        alpha = int(12 * (1 - i / 30))
        shade_draw.line([(670 - i, 90), (670 - i, 530)], fill=(0, 0, 0, alpha))
    canvas.paste(Image.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 0)), shade), mask=shade)


def _draw_phone_case(canvas: Image.Image, draw: ImageDraw.Draw, design: Image.Image, area: tuple):
    """Draw a phone case with rounded corners, camera cutout, and design."""
    case_outer = (55, 50, 495, 900)
    case_inner = (70, 70, 480, 880)
    case_color = (50, 50, 55)
    bezel_color = (40, 40, 45)

    _add_drop_shadow(canvas, case_outer, radius=35, offset=(5, 8), color=(0, 0, 0, 80))

    draw.rounded_rectangle(case_outer, radius=38, fill=case_color)
    draw.rounded_rectangle(case_inner, radius=32, fill=bezel_color)

    area_w = area[2] - area[0]
    area_h = area[3] - area[1]
    design_resized = _smart_crop_to_aspect(design, area_w, area_h)

    mask = Image.new("L", canvas.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(case_inner, radius=32, fill=255)
    canvas.paste(design_resized, (area[0], area[1]), design_resized)

    draw.rounded_rectangle([155, 55, 270, 100], radius=12, fill=(25, 25, 30))
    draw.ellipse([325, 60, 365, 95], fill=(25, 25, 30))
    draw.ellipse([335, 67, 355, 88], outline=(55, 55, 65), width=2)

    screen_glare = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glare_draw = ImageDraw.Draw(screen_glare)
    for i in range(60):
        alpha = int(8 * (1 - i / 60))
        glare_draw.line([(480 - i, 70), (480 - i, 880)], fill=(255, 255, 255, alpha))
    canvas.paste(Image.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 0)), screen_glare), mask=screen_glare)


def _draw_sticker(canvas: Image.Image, draw: ImageDraw.Draw, design: Image.Image, area: tuple):
    """Draw a sticker with white border, slight rotation, and drop shadow."""
    border = 12
    sticker_bbox = (area[0] - border, area[1] - border, area[2] + border, area[3] + border)

    _add_drop_shadow(canvas, sticker_bbox, radius=20, offset=(4, 5), color=(0, 0, 0, 45))

    draw.rounded_rectangle(sticker_bbox, radius=20, fill=(255, 255, 255))

    area_w = area[2] - area[0]
    area_h = area[3] - area[1]
    design_resized = _smart_crop_to_aspect(design, area_w, area_h)
    canvas.paste(design_resized, (area[0], area[1]), design_resized)

    draw.rounded_rectangle(sticker_bbox, radius=20, outline=(220, 220, 220), width=2)

    surface_hint = _load_font(11)
    draw.text((canvas.size[0] // 2 - 60, canvas.size[1] - 40), "vinyl · waterproof · UV-safe", fill=(120, 120, 120), font=surface_hint)


def _draw_hat(canvas: Image.Image, draw: ImageDraw.Draw, design: Image.Image, area: tuple):
    """Draw a structured trucker cap with front panel and design."""
    cap_color = (45, 45, 50)
    panel_color = (55, 55, 60)
    brim_color = (35, 35, 40)

    draw.ellipse([120, 30, 680, 360], fill=cap_color)
    draw.rounded_rectangle([160, 100, 640, 450], radius=20, fill=panel_color)
    draw.ellipse([140, 400, 660, 520], fill=brim_color)
    draw.ellipse([150, 395, 650, 510], fill=(50, 50, 55))

    _add_drop_shadow(canvas, (160, 100, 640, 450), radius=15, offset=(3, 4), color=(0, 0, 0, 40))

    area_w = area[2] - area[0]
    area_h = area[3] - area[1]
    design_resized = _smart_crop_to_aspect(design, area_w, area_h)
    canvas.paste(design_resized, (area[0], area[1]), design_resized)

    draw.ellipse([375, 15, 425, 50], fill=(65, 65, 70))

    draw.line([(400, 35), (400, 100)], fill=(70, 70, 75), width=2)

    brim_shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    bs_draw = ImageDraw.Draw(brim_shade)
    for i in range(20):
        alpha = int(18 * (1 - i / 20))
        bs_draw.ellipse([145, 400 + i, 655, 515 + i], fill=(0, 0, 0, alpha))
    canvas.paste(Image.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, 0)), brim_shade), mask=brim_shade)


def generate_mockup(product_type: str, design_bytes: bytes, archetype: str | None = None) -> bytes | None:
    """Generate a mockup composite for a product type. Returns PNG bytes or None."""
    template = _TEMPLATES.get(product_type)
    if not template:
        return None

    try:
        canvas = Image.new("RGBA", template["size"], (*template["bg_color"], 255))
        draw = ImageDraw.Draw(canvas)

        design = Image.open(io.BytesIO(design_bytes)).convert("RGBA")

        is_text_design = archetype in ("text_only", "typographic", "text_icon")
        if is_text_design and "design_area_text" in template:
            area = template["design_area_text"]
        else:
            area = template["design_area"]

        if product_type == "mug":
            _draw_mug(canvas, draw, design, area)
        elif product_type == "phone_case":
            _draw_phone_case(canvas, draw, design, area)
        elif product_type == "sticker":
            _draw_sticker(canvas, draw, design, area)
        elif product_type == "hat":
            _draw_hat(canvas, draw, design, area)
        elif product_type == "tshirt":
            area_w = area[2] - area[0]
            area_h = area[3] - area[1]
            design_resized = _smart_crop_to_aspect(design, area_w, area_h)
            canvas.paste(design_resized, (area[0], area[1]), design_resized)

            collar_color = (50, 50, 50)
            draw.arc([300, 15, 500, 120], start=200, end=340, fill=collar_color, width=3)
            draw.line([(200, 200), (100, 300), (100, 400), (200, 350)], fill=collar_color, width=2)
            draw.line([(600, 200), (700, 300), (700, 400), (600, 350)], fill=collar_color, width=2)
            draw.rounded_rectangle([150, 180, 650, 900], radius=20, outline=collar_color, width=2)
        elif product_type == "hoodie":
            area_w = area[2] - area[0]
            area_h = area[3] - area[1]
            design_resized = _smart_crop_to_aspect(design, area_w, area_h)
            canvas.paste(design_resized, (area[0], area[1]), design_resized)

            outline = (50, 50, 50)
            draw.rounded_rectangle([140, 180, 660, 920], radius=20, outline=outline, width=2)
            draw.arc([310, 10, 490, 140], start=200, end=340, fill=outline, width=3)
            draw.line([(200, 200), (80, 320), (80, 500), (140, 450)], fill=outline, width=2)
            draw.line([(600, 200), (720, 320), (720, 500), (660, 450)], fill=outline, width=2)
            # Hood
            draw.arc([250, -30, 550, 180], start=200, end=340, fill=outline, width=2)
            # Kangaroo pocket
            draw.rounded_rectangle([260, 650, 540, 760], radius=15, outline=outline, width=2)
        elif product_type == "long_sleeve":
            area_w = area[2] - area[0]
            area_h = area[3] - area[1]
            design_resized = _smart_crop_to_aspect(design, area_w, area_h)
            canvas.paste(design_resized, (area[0], area[1]), design_resized)

            outline = (50, 50, 50)
            draw.arc([300, 15, 500, 120], start=200, end=340, fill=outline, width=3)
            draw.line([(200, 200), (60, 340), (60, 700), (140, 680)], fill=outline, width=2)
            draw.line([(600, 200), (740, 340), (740, 700), (660, 680)], fill=outline, width=2)
            draw.rounded_rectangle([150, 180, 650, 900], radius=20, outline=outline, width=2)
            # Cuffs
            draw.rectangle([55, 680, 145, 710], outline=outline, width=2)
            draw.rectangle([655, 680, 745, 710], outline=outline, width=2)
        else:
            area_w = area[2] - area[0]
            area_h = area[3] - area[1]
            design_resized = _smart_crop_to_aspect(design, area_w, area_h)
            canvas.paste(design_resized, (area[0], area[1]), design_resized)

        label_font = _load_font(14)
        label = template.get("label", product_type)
        lw = label_font.getbbox(label)[2]
        draw.text((template["size"][0] - lw - 15, template["size"][1] - 28), label, fill=(120, 120, 120), font=label_font)

        final = canvas.convert("RGB")
        buf = io.BytesIO()
        final.save(buf, format="PNG", quality=95)
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
