from app.services.catalog.colors import (
    normalize_color_name, hex_to_rgb, brightness, is_light_hex, nearest_color,
)


def test_normalize_collapses_case_and_whitespace():
    assert normalize_color_name("Navy  Blue") == "navy blue"
    assert normalize_color_name(" Heather Grey ") == "heather grey"


def test_hex_to_rgb_handles_hash_and_no_hash():
    assert hex_to_rgb("#ffffff") == (255, 255, 255)
    assert hex_to_rgb("000000") == (0, 0, 0)


def test_brightness_formula():
    # (255*299 + 255*587 + 255*114)/1000 = 255
    assert brightness((255, 255, 255)) == 255.0
    assert brightness((0, 0, 0)) == 0.0


def test_is_light_threshold():
    assert is_light_hex("#ffffff") is True
    assert is_light_hex("#000000") is False
    # mid grey 0x80 = 128 -> not > 128 -> dark
    assert is_light_hex("#808080") is False


def test_nearest_color_picks_closest_hex():
    candidates = {"black": "#000000", "white": "#ffffff", "navy": "#001f3f"}
    assert nearest_color("#101010", candidates) == "black"
    assert nearest_color("#f0f0f0", candidates) == "white"


def test_nearest_color_empty_returns_none():
    assert nearest_color("#123456", {}) is None
