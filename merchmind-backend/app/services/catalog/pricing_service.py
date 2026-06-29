"""Variant pricing lookups backed by the cached price map."""

_PRICES_KEY = "catalog:prices"


def get_price(cache, variant_id: int) -> dict:
    data = cache.get_json(_PRICES_KEY) or {}
    cost = (data.get("map") or {}).get(str(variant_id))
    return {"cost": cost, "currency": "USD"}


def merge_prices(cache, price_updates: dict[int, float]) -> None:
    data = cache.get_json(_PRICES_KEY) or {"map": {}}
    pmap = data.get("map", {})
    for vid, cost in price_updates.items():
        pmap[str(vid)] = cost
    cache.set_json(_PRICES_KEY, {"map": pmap})


def price_range_from_library(color_library: dict) -> dict:
    costs = [v["cost"] for v in color_library.values() if v.get("cost")]
    if not costs:
        return {"min": None, "max": None, "currency": "USD"}
    return {"min": min(costs), "max": max(costs), "currency": "USD"}
