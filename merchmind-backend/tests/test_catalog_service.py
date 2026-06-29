from unittest.mock import patch
from app.services.catalog.cache import CatalogCache
from app.services.catalog.catalog_service import CatalogService
from tests.test_catalog_cache import FakeRedis


def _svc():
    return CatalogService(cache=CatalogCache(client=FakeRedis()))


def test_get_colors_reads_harvested_library():
    svc = _svc()
    # Seed a harvested color library directly into cache.
    svc.cache.set_json("catalog:colors:5:99", {"library": {
        "black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                  "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/b.png"},
        "white": {"display_name": "White", "hex": "#ffffff", "is_light": True,
                  "variant_id": 14, "cost": 8.5, "front_url": ""},
    }})
    colors = svc.get_colors(5, 99)
    by_name = {c["name"]: c for c in colors}
    assert by_name["Black"]["is_light"] is False
    assert by_name["Black"]["has_mockup"] is True
    assert by_name["White"]["has_mockup"] is False


def test_get_enabled_variant_ids_spreads_across_colors():
    svc = _svc()
    svc.cache.set_json("catalog:variants:5:99", {"color_index": {
        "black": {"display_name": "Black", "variant_ids": [11, 12], "sizes": ["S", "M"]},
        "navy": {"display_name": "Navy", "variant_ids": [13, 14], "sizes": ["S", "M"]},
        "white": {"display_name": "White", "variant_ids": [15], "sizes": ["S"]},
    }})
    ids = svc.get_enabled_variant_ids(5, 99, max_colors=2)
    # 2 colors -> first two color groups' variant ids
    assert set(ids) == {11, 12, 13, 14}


def test_ingest_product_merges_library_and_prices():
    svc = _svc()
    product_json = {
        "options": [{"name": "Colors", "type": "color", "values": [
            {"id": 521, "title": "Black", "colors": ["#000000"]}]}],
        "variants": [{"id": 11, "options": [521], "cost": 850, "is_enabled": True}],
        "images": [{"src": "https://cdn/b.png", "variant_ids": [11], "position": "front"}],
    }
    lib = svc.ingest_product(5, 99, product_json)
    assert lib["black"]["front_url"] == "https://cdn/b.png"
    assert svc.get_price(11) == {"cost": 8.5, "currency": "USD"}


def test_refresh_populates_blueprints_and_variants():
    svc = _svc()
    with patch("app.services.catalog.catalog_service.blueprint_service.fetch_blueprints",
               return_value=[{"id": 5, "title": "Tee", "brand": "BC", "model": "3001"}]), \
         patch("app.services.catalog.catalog_service.provider_service.fetch_providers",
               return_value=[{"id": 99, "title": "Choice"}]), \
         patch("app.services.catalog.catalog_service.variant_service.fetch_variants",
               return_value=[{"id": 11, "color": "Black", "size": "S"}]), \
         patch.object(svc, "_bootstrap_from_shop_products", return_value=None):
        svc.refresh()
    assert svc.get_blueprints()[0]["id"] == 5
    assert svc.get_variants(5, 99)[0]["id"] == 11
