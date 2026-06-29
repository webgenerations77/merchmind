from types import SimpleNamespace
from app.services.catalog.product_apply import apply_catalog_colors


class FakeCatalog:
    def __init__(self, library):
        self._library = library

    def ingest_product(self, bp, prov, pj):
        return self._library


def test_apply_sets_color_mockups_and_default_color():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    library = {
        "black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                  "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/black.png"},
        "white": {"display_name": "White", "hex": "#ffffff", "is_light": True,
                  "variant_id": 14, "cost": 8.5, "front_url": ""},
    }
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog(library))
    assert product.color_mockups == {"Black": "https://cdn/black.png", "White": ""}
    # Default = first color that actually has a mockup
    assert product.selected_color == "Black"


def test_apply_no_mockups_defaults_to_first_color():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    library = {"navy": {"display_name": "Navy", "hex": "#001f3f", "is_light": False,
                        "variant_id": 9, "cost": 9.0, "front_url": ""}}
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog(library))
    assert product.selected_color == "Navy"


def test_apply_empty_library_is_noop():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog({}))
    assert product.color_mockups == {}
    assert product.selected_color is None
