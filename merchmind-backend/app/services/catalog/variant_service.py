"""Fetch variants per blueprint+provider and group them into a color index."""
from app.services.catalog.colors import normalize_color_name


def _catalog_get(path: str):
    # Lazy import to avoid a circular import (printify_publisher imports catalog_service).
    from app.services.publishing.printify_publisher import get_printify_service
    return get_printify_service()._request("GET", path)


def fetch_variants(blueprint_id: int, provider_id: int) -> list[dict]:
    data = _catalog_get(
        f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
    )
    raw = data.get("variants", data.get("data", [])) if isinstance(data, dict) else data
    out = []
    for v in raw:
        opts = v.get("options", {}) or {}
        out.append({"id": v["id"], "color": opts.get("color", ""), "size": opts.get("size", "")})
    return out


def build_color_index(variants: list[dict]) -> dict:
    """Group variants by normalized color name -> {display_name, variant_ids, sizes}."""
    index: dict[str, dict] = {}
    for v in variants:
        color = v.get("color", "")
        if not color:
            continue
        key = normalize_color_name(color)
        entry = index.setdefault(key, {"display_name": color, "variant_ids": [], "sizes": []})
        entry["variant_ids"].append(v["id"])
        size = v.get("size", "")
        if size and size not in entry["sizes"]:
            entry["sizes"].append(size)
    return index
