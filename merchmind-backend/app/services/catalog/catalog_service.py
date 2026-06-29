"""Orchestrates the Printify catalog: fetch -> cache -> serve, plus product harvest."""
import logging
import time
from functools import lru_cache

from app.config import settings
from app.services.catalog import (
    blueprint_service, provider_service, variant_service, mockup_service, pricing_service,
)
from app.services.catalog.cache import CatalogCache, get_catalog_cache, is_stale
from app.services.catalog.colors import normalize_color_name

logger = logging.getLogger(__name__)

_BLUEPRINTS_KEY = "catalog:blueprints"


def _variants_key(bp, prov):
    return f"catalog:variants:{bp}:{prov}"


def _colors_key(bp, prov):
    return f"catalog:colors:{bp}:{prov}"


class CatalogService:
    def __init__(self, cache: CatalogCache | None = None):
        self.cache = cache if cache is not None else get_catalog_cache()

    # ---- reads (cache-only, never block) ----
    def get_blueprints(self) -> list[dict]:
        data = self.cache.get_json(_BLUEPRINTS_KEY)
        return data.get("items", []) if data else []

    def get_blueprint(self, blueprint_id: int) -> dict | None:
        return next((b for b in self.get_blueprints() if b["id"] == blueprint_id), None)

    def get_providers(self, blueprint_id: int) -> list[dict]:
        data = self.cache.get_json(f"catalog:providers:{blueprint_id}")
        return data.get("items", []) if data else []

    def get_variants(self, blueprint_id: int, provider_id: int) -> list[dict]:
        data = self.cache.get_json(_variants_key(blueprint_id, provider_id))
        return data.get("variants", []) if data else []

    def _color_index(self, blueprint_id: int, provider_id: int) -> dict:
        data = self.cache.get_json(_variants_key(blueprint_id, provider_id))
        return data.get("color_index", {}) if data else {}

    def _color_library(self, blueprint_id: int, provider_id: int) -> dict:
        data = self.cache.get_json(_colors_key(blueprint_id, provider_id))
        return data.get("library", {}) if data else {}

    def get_colors(self, blueprint_id: int, provider_id: int) -> list[dict]:
        lib = self._color_library(blueprint_id, provider_id)
        return [
            {"name": v["display_name"], "hex": v["hex"], "is_light": v["is_light"],
             "has_mockup": bool(v.get("front_url"))}
            for v in lib.values()
        ]

    def get_sizes(self, blueprint_id: int, provider_id: int) -> list[str]:
        sizes: list[str] = []
        for entry in self._color_index(blueprint_id, provider_id).values():
            for s in entry.get("sizes", []):
                if s not in sizes:
                    sizes.append(s)
        return sizes

    def get_variant(self, blueprint_id: int, provider_id: int, color: str, size: str | None = None) -> int | None:
        lib = self._color_library(blueprint_id, provider_id)
        if lib:
            vid = mockup_service.resolve_variant(lib, color)
            if vid is not None:
                return vid
        # Fall back to the color index (no hex, exact-name only)
        idx = self._color_index(blueprint_id, provider_id)
        entry = idx.get(normalize_color_name(color))
        return entry["variant_ids"][0] if entry and entry["variant_ids"] else None

    def get_enabled_variant_ids(self, blueprint_id: int, provider_id: int, max_colors: int) -> list[int]:
        idx = self._color_index(blueprint_id, provider_id)
        ids: list[int] = []
        for entry in list(idx.values())[:max_colors]:
            ids.extend(entry.get("variant_ids", []))
        return ids

    def get_mockups(self, blueprint_id: int, provider_id: int) -> dict:
        return {k: v.get("front_url", "") for k, v in self._color_library(blueprint_id, provider_id).items()}

    def get_price(self, variant_id: int) -> dict:
        return pricing_service.get_price(self.cache, variant_id)

    def get_price_range(self, blueprint_id: int, provider_id: int) -> dict:
        return pricing_service.price_range_from_library(self._color_library(blueprint_id, provider_id))

    def search(self, query: str) -> list[dict]:
        q = (query or "").lower()
        return [b for b in self.get_blueprints() if q in b["title"].lower() or q in b.get("brand", "").lower()]

    # ---- writes ----
    def ingest_product(self, blueprint_id: int, provider_id: int, product_json: dict) -> dict:
        """Harvest hex/cost/mockups from a created product and merge into the cached library."""
        harvested = mockup_service.harvest_from_product(product_json)
        existing = self._color_library(blueprint_id, provider_id)
        existing.update(harvested)
        self.cache.set_json(_colors_key(blueprint_id, provider_id), {"library": existing})
        pricing_service.merge_prices(
            self.cache, {v["variant_id"]: v["cost"] for v in harvested.values() if v.get("cost")}
        )
        logger.info("catalog.ingest_product bp=%s prov=%s colors=%d", blueprint_id, provider_id, len(harvested))
        return existing

    def refresh(self) -> None:
        now = time.time()
        if self.cache.in_backoff(now):
            logger.info("catalog.refresh skipped (in backoff)")
            return
        try:
            blueprints = blueprint_service.fetch_blueprints()
            self.cache.set_json(_BLUEPRINTS_KEY, {"items": blueprints})
            from app.services.publishing.printify_publisher import _BLUEPRINT_MAP, _PROVIDER_MAP
            for product_type, bp in _BLUEPRINT_MAP.items():
                prov = _PROVIDER_MAP.get(product_type, 99)
                providers = provider_service.fetch_providers(bp)
                self.cache.set_json(f"catalog:providers:{bp}", {"items": providers})
                variants = variant_service.fetch_variants(bp, prov)
                self.cache.set_json(_variants_key(bp, prov), {
                    "variants": variants,
                    "color_index": variant_service.build_color_index(variants),
                })
            self._bootstrap_from_shop_products()
            self.cache.clear_backoff()
            logger.info("catalog.refresh complete blueprints=%d", len(blueprints))
        except Exception as e:
            logger.error("catalog.refresh failed: %s", e)
            self.cache.record_failure(now)

    def _bootstrap_from_shop_products(self) -> None:
        """Seed the color library (hex/mockups) by ingesting existing shop products."""
        try:
            from app.services.publishing.printify_publisher import get_printify_service, _BLUEPRINT_MAP, _PROVIDER_MAP
            svc = get_printify_service()
            data = svc._request("GET", f"/shops/{settings.PRINTIFY_SHOP_ID}/products.json")
            products = data.get("data", data if isinstance(data, list) else [])
            bp_to_type = {bp: t for t, bp in _BLUEPRINT_MAP.items()}
            for summary in products[:50]:
                pid = summary.get("id")
                bp = summary.get("blueprint_id")
                prov = summary.get("print_provider_id") or _PROVIDER_MAP.get(bp_to_type.get(bp, ""), 99)
                if not pid or not bp:
                    continue
                full = svc._request("GET", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{pid}.json")
                self.ingest_product(bp, prov, full)
        except Exception as e:
            logger.warning("catalog.bootstrap_from_shop_products failed (non-fatal): %s", e)

    def ensure_fresh(self) -> None:
        now = time.time()
        if is_stale(self.cache.refreshed_at(_BLUEPRINTS_KEY), settings.PRINTIFY_CATALOG_TTL_HOURS, now):
            self.refresh()


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService()
