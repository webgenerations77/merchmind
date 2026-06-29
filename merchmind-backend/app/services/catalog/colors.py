"""Pure color math helpers for the Printify catalog service. No external deps."""
import re


def normalize_color_name(name: str) -> str:
    """Lowercase and collapse internal whitespace for use as a stable key."""
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = (hex_str or "").lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_str!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def brightness(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (r * 299 + g * 587 + b * 114) / 1000


def is_light_hex(hex_str: str) -> bool:
    return brightness(hex_to_rgb(hex_str)) > 128


def nearest_color(target_hex: str, candidates: dict[str, str]) -> str | None:
    """Return the normalized name of the candidate whose hex is closest to target."""
    if not candidates:
        return None
    tr, tg, tb = hex_to_rgb(target_hex)
    best_name, best_dist = None, None
    for name, hex_str in candidates.items():
        try:
            r, g, b = hex_to_rgb(hex_str)
        except ValueError:
            continue
        dist = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
        if best_dist is None or dist < best_dist:
            best_name, best_dist = name, dist
    return best_name
