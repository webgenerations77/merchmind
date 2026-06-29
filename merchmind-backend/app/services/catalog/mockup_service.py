"""Harvest per-color hex/cost/mockup data from a created Printify product, and
resolve colors to variants / mockup URLs (with nearest-hex fallback)."""
import logging

from app.services.catalog.colors import is_light_hex, nearest_color, normalize_color_name

logger = logging.getLogger(__name__)


def _color_option(product_json: dict) -> dict:
    """Return {value_id: {'title': str, 'hex': str}} for the color option."""
    for opt in product_json.get("options", []):
        if opt.get("type") == "color" or "color" in opt.get("name", "").lower():
            out = {}
            for val in opt.get("values", []):
                colors = val.get("colors") or []
                out[val["id"]] = {"title": val.get("title", ""), "hex": colors[0] if colors else ""}
            return out
    return {}


def harvest_from_product(product_json: dict) -> dict:
    """Build {normalized_color: {display_name, hex, is_light, variant_id, cost, front_url}}."""
    color_values = _color_option(product_json)
    color_value_ids = set(color_values.keys())

    # variant_id -> color value_id
    variant_color: dict[int, int] = {}
    library: dict[str, dict] = {}
    for v in product_json.get("variants", []):
        vid = v["id"]
        cvid = next((o for o in v.get("options", []) if o in color_value_ids), None)
        if cvid is None:
            continue
        variant_color[vid] = cvid
        meta = color_values[cvid]
        hex_str = meta["hex"]
        if not hex_str:
            continue
        key = normalize_color_name(meta["title"])
        if key not in library:
            try:
                light = is_light_hex(hex_str)
            except ValueError:
                logger.warning("catalog.harvest bad hex %r for %s", hex_str, meta["title"])
                continue
            library[key] = {
                "display_name": meta["title"],
                "hex": hex_str,
                "is_light": light,
                "variant_id": vid,
                "cost": (v.get("cost") or 0) / 100.0,
                "front_url": "",
            }

    # Attach front mockup URL by matching image.variant_ids -> a color's variants
    for img in product_json.get("images", []):
        if img.get("position") not in ("front", "default", None):
            continue
        src = img.get("src", "")
        if not src:
            continue
        for vid in img.get("variant_ids", []):
            cvid = variant_color.get(vid)
            if cvid is None:
                continue
            key = normalize_color_name(color_values[cvid]["title"])
            if key in library and not library[key]["front_url"]:
                library[key]["front_url"] = src

    return library


def _hex_candidates(color_library: dict) -> dict[str, str]:
    return {k: v["hex"] for k, v in color_library.items() if v.get("hex")}


def resolve_variant(color_library: dict, color: str) -> int | None:
    key = normalize_color_name(color)
    if key in color_library:
        return color_library[key]["variant_id"]
    near = nearest_color(color_library.get(key, {}).get("hex", "") or "#000000", _hex_candidates(color_library))
    return color_library[near]["variant_id"] if near else None


def get_mockup_url(color_library: dict, color: str) -> str | None:
    key = normalize_color_name(color)
    if key in color_library:
        return color_library[key]["front_url"] or None
    target_hex = color_library.get(key, {}).get("hex")
    if not target_hex:
        return None
    near = nearest_color(target_hex, _hex_candidates(color_library))
    return color_library[near]["front_url"] if near else None
