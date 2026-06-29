from unittest.mock import patch
from app.services.publishing.printify_publisher import PrintifyService


def test_uses_catalog_spread_when_available():
    svc = PrintifyService()
    all_variants = [{"id": i} for i in range(1, 60)]
    with patch("app.services.publishing.printify_publisher.get_catalog_service") as gcs:
        gcs.return_value.get_enabled_variant_ids.return_value = [11, 12, 13, 14]
        ids = svc._select_enabled_variant_ids(5, 99, all_variants)
    assert ids == [11, 12, 13, 14]


def test_falls_back_to_first_20_when_catalog_empty():
    svc = PrintifyService()
    all_variants = [{"id": i} for i in range(1, 60)]
    with patch("app.services.publishing.printify_publisher.get_catalog_service") as gcs:
        gcs.return_value.get_enabled_variant_ids.return_value = []
        ids = svc._select_enabled_variant_ids(5, 99, all_variants)
    assert ids == list(range(1, 21))
