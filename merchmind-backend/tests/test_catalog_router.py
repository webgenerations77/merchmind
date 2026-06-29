from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)
HEADERS = {"X-API-Key": settings.APP_API_KEY}


def test_colors_endpoint_returns_swatches():
    fake = [{"name": "Black", "hex": "#000000", "is_light": False, "has_mockup": True}]
    with patch("app.routers.catalog.get_catalog_service") as gcs:
        gcs.return_value.get_colors.return_value = fake
        r = client.get("/catalog/colors", params={"blueprint_id": 5, "provider_id": 99}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"][0]["name"] == "Black"


def test_mockup_endpoint_returns_url_and_meta():
    lib = {"black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                     "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/b.png"}}
    with patch("app.routers.catalog.get_catalog_service") as gcs:
        svc = gcs.return_value
        svc._color_library.return_value = lib
        svc.get_mockups.return_value = {"black": "https://cdn/b.png"}
        with patch("app.routers.catalog.mockup_service.get_mockup_url", return_value="https://cdn/b.png"):
            r = client.get("/catalog/mockup",
                           params={"blueprint_id": 5, "provider_id": 99, "color": "Black"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["data"]["mockup_url"] == "https://cdn/b.png"


def test_requires_api_key():
    r = client.get("/catalog/colors", params={"blueprint_id": 5, "provider_id": 99})
    assert r.status_code in (401, 403)
