"""Tests for text compositor service."""
import io
from PIL import Image
from app.services.design.text_compositor import (
    composite_text_on_image,
    should_composite,
    _wrap_text,
    _region_luminance,
    _pick_text_color,
    _load_font,
)


def _make_test_image(w=800, h=800, color=(100, 100, 200, 255)) -> bytes:
    img = Image.new("RGBA", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestShouldComposite:
    def test_hybrid_composites(self):
        assert should_composite("hybrid") is True

    def test_text_icon_composites(self):
        assert should_composite("text_icon") is True

    def test_illustration_does_not(self):
        assert should_composite("illustration") is False

    def test_text_only_does_not(self):
        assert should_composite("text_only") is False

    def test_typographic_does_not(self):
        assert should_composite("typographic") is False


class TestCompositeTextOnImage:
    def test_returns_valid_png(self):
        img_bytes = _make_test_image()
        result = composite_text_on_image(img_bytes, "HELLO WORLD")
        img = Image.open(io.BytesIO(result))
        assert img.format == "PNG"
        assert img.mode == "RGBA"
        assert img.size == (800, 800)

    def test_preserves_dimensions(self):
        img_bytes = _make_test_image(1200, 1200)
        result = composite_text_on_image(img_bytes, "Test", secondary_text="Sub")
        img = Image.open(io.BytesIO(result))
        assert img.size == (1200, 1200)

    def test_with_secondary_text(self):
        img_bytes = _make_test_image()
        result = composite_text_on_image(
            img_bytes, "Primary", secondary_text="Secondary text here"
        )
        assert len(result) > 0
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 800)

    def test_long_text_wraps(self):
        img_bytes = _make_test_image()
        result = composite_text_on_image(
            img_bytes, "This is a really long slogan that should wrap onto multiple lines"
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 800)

    def test_modifies_image(self):
        img_bytes = _make_test_image()
        result = composite_text_on_image(img_bytes, "CHANGE")
        assert result != img_bytes


class TestTextColor:
    def test_dark_region_gets_white_text(self):
        img = Image.new("RGBA", (100, 100), (20, 20, 20, 255))
        color = _pick_text_color(img, 50, 100)
        assert color == (255, 255, 255, 255)

    def test_light_region_gets_dark_text(self):
        img = Image.new("RGBA", (100, 100), (240, 240, 240, 255))
        color = _pick_text_color(img, 50, 100)
        assert color == (20, 20, 20, 255)


class TestWrapText:
    def test_short_text_single_line(self):
        font = _load_font(36)
        lines = _wrap_text("Hi", font, 500)
        assert len(lines) == 1
        assert lines[0] == "Hi"

    def test_long_text_wraps(self):
        font = _load_font(36)
        lines = _wrap_text("This is a long sentence that should wrap", font, 200)
        assert len(lines) > 1


class TestRegionLuminance:
    def test_black_region(self):
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
        lum = _region_luminance(img, 0, 100)
        assert lum < 10

    def test_white_region(self):
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        lum = _region_luminance(img, 0, 100)
        assert lum > 240
