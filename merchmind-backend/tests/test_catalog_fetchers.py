from unittest.mock import patch
from app.services.catalog import blueprint_service, provider_service, variant_service


def test_fetch_blueprints_maps_fields():
    fake = [{"id": 5, "title": "Unisex Tee", "brand": "Bella+Canvas", "model": "3001", "x": 1}]
    with patch.object(blueprint_service, "_catalog_get", return_value=fake) as m:
        out = blueprint_service.fetch_blueprints()
    m.assert_called_once_with("/catalog/blueprints.json")
    assert out == [{"id": 5, "title": "Unisex Tee", "brand": "Bella+Canvas", "model": "3001"}]


def test_fetch_providers_maps_fields():
    fake = [{"id": 99, "title": "Printify Choice", "location": {}}]
    with patch.object(provider_service, "_catalog_get", return_value=fake):
        out = provider_service.fetch_providers(5)
    assert out == [{"id": 99, "title": "Printify Choice"}]


def test_fetch_variants_extracts_color_and_size():
    fake = {"variants": [
        {"id": 11, "title": "Black / S", "options": {"color": "Black", "size": "S"}},
        {"id": 12, "title": "Black / M", "options": {"color": "Black", "size": "M"}},
        {"id": 13, "title": "Heather Navy / S", "options": {"color": "Heather Navy", "size": "S"}},
    ]}
    with patch.object(variant_service, "_catalog_get", return_value=fake):
        out = variant_service.fetch_variants(5, 99)
    assert {"id": 11, "color": "Black", "size": "S"} in out
    assert len(out) == 3


def test_build_color_index_groups_by_normalized_color():
    variants = [
        {"id": 11, "color": "Black", "size": "S"},
        {"id": 12, "color": "Black", "size": "M"},
        {"id": 13, "color": "Heather Navy", "size": "S"},
    ]
    idx = variant_service.build_color_index(variants)
    assert set(idx.keys()) == {"black", "heather navy"}
    assert idx["black"]["display_name"] == "Black"
    assert sorted(idx["black"]["variant_ids"]) == [11, 12]
    assert idx["black"]["sizes"] == ["S", "M"]
