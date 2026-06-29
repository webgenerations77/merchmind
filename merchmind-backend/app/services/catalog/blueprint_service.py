"""Fetch blueprint metadata from the Printify Catalog API."""


def _catalog_get(path: str):
    # Lazy import to avoid a circular import (printify_publisher imports catalog_service).
    from app.services.publishing.printify_publisher import get_printify_service
    return get_printify_service()._request("GET", path)


def fetch_blueprints() -> list[dict]:
    data = _catalog_get("/catalog/blueprints.json")
    items = data if isinstance(data, list) else data.get("data", [])
    return [
        {"id": b["id"], "title": b.get("title", ""), "brand": b.get("brand", ""), "model": b.get("model", "")}
        for b in items
    ]
