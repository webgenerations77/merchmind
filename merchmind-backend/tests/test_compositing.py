"""Tests for design compositing: alpha handling so designs blend into the
garment instead of showing a hard rectangular box."""
import io

from PIL import Image

from app.services.design.post_processor import has_transparency
from app.services.design.mockup_generator import _composite_design


def _opaque(mode="RGBA", color=(10, 20, 30, 255), size=(64, 64)):
    return Image.new(mode, size, color)


def test_has_transparency_false_for_fully_opaque_rgba():
    assert has_transparency(_opaque()) is False


def test_has_transparency_false_for_rgb():
    assert has_transparency(Image.new("RGB", (32, 32), (1, 2, 3))) is False


def test_has_transparency_true_when_any_pixel_transparent():
    img = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
    img.putpixel((0, 0), (0, 0, 0, 0))
    assert has_transparency(img) is True


def test_composite_design_blends_transparent_edges_no_box():
    # A design that is transparent everywhere except a small opaque center.
    canvas = Image.new("RGBA", (800, 1000), (200, 50, 50, 255))  # garment color
    design = Image.new("RGBA", (400, 400), (0, 0, 0, 0))         # fully transparent
    design.putpixel((200, 200), (0, 255, 0, 255))               # one opaque dot
    area = (200, 200, 600, 600)

    _composite_design(canvas, design, area)

    # A corner of the paste area must remain the garment color (the transparent
    # design edge blended in), not a black/colored box.
    assert canvas.getpixel((area[0] + 2, area[1] + 2))[:3] == (200, 50, 50)


def test_composite_design_converts_rgb_input_without_error():
    canvas = Image.new("RGBA", (800, 1000), (255, 255, 255, 255))
    design = Image.new("RGB", (400, 400), (12, 34, 56))  # no alpha channel
    _composite_design(canvas, design, (200, 200, 600, 600))
    # Opaque RGB design fills the area (its alpha is fully opaque after convert).
    assert canvas.getpixel((400, 400))[:3] == (12, 34, 56)
