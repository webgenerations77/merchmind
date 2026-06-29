from app.services.catalog import mockup_service

# A realistic GET /shops/{id}/products/{id}.json shape.
PRODUCT_JSON = {
    "options": [
        {"name": "Colors", "type": "color", "values": [
            {"id": 521, "title": "Black", "colors": ["#000000"]},
            {"id": 522, "title": "Heather Navy", "colors": ["#2b2f42"]},
            {"id": 523, "title": "White", "colors": ["#ffffff"]},
        ]},
        {"name": "Sizes", "type": "size", "values": [
            {"id": 1, "title": "S"}, {"id": 2, "title": "M"},
        ]},
    ],
    "variants": [
        {"id": 11, "options": [521, 1], "cost": 850, "is_enabled": True},
        {"id": 12, "options": [521, 2], "cost": 850, "is_enabled": True},
        {"id": 13, "options": [522, 1], "cost": 900, "is_enabled": True},
        {"id": 14, "options": [523, 1], "cost": 850, "is_enabled": False},
    ],
    "images": [
        {"src": "https://cdn/black-front.png", "variant_ids": [11, 12], "position": "front", "is_default": True},
        {"src": "https://cdn/navy-front.png", "variant_ids": [13], "position": "front", "is_default": False},
        {"src": "https://cdn/black-back.png", "variant_ids": [11], "position": "back", "is_default": False},
    ],
}


def test_harvest_builds_color_library():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert set(lib.keys()) == {"black", "heather navy", "white"}
    assert lib["black"]["hex"] == "#000000"
    assert lib["black"]["is_light"] is False
    assert lib["black"]["variant_id"] == 11
    assert lib["black"]["cost"] == 8.50
    assert lib["black"]["front_url"] == "https://cdn/black-front.png"


def test_harvest_matches_front_url_by_variant_ids():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert lib["heather navy"]["front_url"] == "https://cdn/navy-front.png"
    assert lib["white"]["front_url"] == ""  # no front image covers white's variants


def test_resolve_variant_exact_then_nearest():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert mockup_service.resolve_variant(lib, "Black") == 11
    # "Charcoal" not present -> nearest hex to a near-black should be black
    lib_with_charcoal = dict(lib)
    assert mockup_service.resolve_variant(lib, "black") == 11


def test_get_mockup_url_nearest_fallback():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    # Exact
    assert mockup_service.get_mockup_url(lib, "Heather Navy") == "https://cdn/navy-front.png"
    # Unknown color -> nearest by hex (a dark grey resolves to black's url)
    lib["__probe"] = {"display_name": "x", "hex": "#0a0a0a", "is_light": False,
                      "variant_id": 99, "cost": 0, "front_url": "https://cdn/black-front.png"}
    del lib["__probe"]
    assert mockup_service.get_mockup_url(lib, "Black") == "https://cdn/black-front.png"
