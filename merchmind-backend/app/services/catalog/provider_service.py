"""Fetch print providers per blueprint from the Printify Catalog API."""


def _catalog_get(path: str):
    # Lazy import to avoid a circular import (printify_publisher imports catalog_service).
    from app.services.publishing.printify_publisher import get_printify_service
    return get_printify_service()._request("GET", path)


def fetch_providers(blueprint_id: int) -> list[dict]:
    data = _catalog_get(f"/catalog/blueprints/{blueprint_id}/print_providers.json")
    items = data if isinstance(data, list) else data.get("data", [])
    return [{"id": p["id"], "title": p.get("title", "")} for p in items]
