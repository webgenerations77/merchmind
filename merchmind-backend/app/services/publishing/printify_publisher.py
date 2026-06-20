"""
Printify API client — class-based service for creating products and generating mockups.
Uploads mockup images to Supabase Storage after generation.
"""
import logging
import time
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.exceptions import (
    PrintifyAuthError,
    PrintifyError,
    PrintifyMockupError,
    PrintifyProductError,
    PrintifyRateLimitError,
)
from app.utils.rate_limiter import printify_limiter
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.printify.com/v1"
_TIMEOUT = 30
_MAX_RETRIES = 3

_BLUEPRINT_MAP = {
    "tshirt": 5,
    "mug": 77,
    "hat": 54,
    "phone_case": 194,
    "sticker": 213,
    "poster": 56,
}

_FALLBACK_BASE_COSTS = {
    "tshirt": 8.50,
    "mug": 6.00,
    "hat": 10.00,
    "phone_case": 8.00,
    "sticker": 2.50,
    "poster": 12.00,
}


class PrintifyService:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.PRINTIFY_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MerchMind/1.0",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{_BASE_URL}{path}"
        for attempt in range(_MAX_RETRIES):
            start = time.monotonic()
            try:
                printify_limiter.consume()
                with httpx.Client(timeout=_TIMEOUT) as client:
                    response = client.request(method, url, headers=self._headers(), **kwargs)
                elapsed = round((time.monotonic() - start) * 1000)
                logger.info("printify.request method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code == 401:
                    raise PrintifyAuthError(f"Printify auth failed on {method} {path}") from e
                if code == 429:
                    wait = min(2 ** attempt * 10, 60)
                    logger.warning("printify.rate_limit wait=%ds attempt=%d", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                raise PrintifyProductError(f"Printify {code} on {method} {path}: {e.response.text[:300]}") from e
            except PrintifyAuthError:
                raise
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise PrintifyError(f"Printify request failed after {_MAX_RETRIES} attempts: {e}") from e
        raise PrintifyError("Printify: max retries exceeded")

    def get_blueprint_variants(self, product_type: str, print_provider_id: int = 99) -> list[dict]:
        blueprint_id = _BLUEPRINT_MAP.get(product_type)
        if not blueprint_id:
            raise ValueError(f"Unknown Printify product type: '{product_type}'")
        data = self._request(
            "GET",
            f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json",
        )
        return data.get("data", [])

    def get_base_cost(self, product_type: str, print_provider_id: int = 99) -> float:
        """Return minimum variant cost in dollars. Falls back to industry-standard costs when Printify is unavailable."""
        try:
            variants = self.get_blueprint_variants(product_type, print_provider_id)
            costs = [v.get("cost", 0) / 100.0 for v in variants if v.get("cost")]
            if costs:
                return min(costs)
        except Exception as e:
            logger.warning("printify.get_base_cost API failed, using fallback. product_type=%s error=%s", product_type, e)
        return _FALLBACK_BASE_COSTS.get(product_type, 8.00)

    def get_base_costs(self, print_provider_id: int = 99) -> dict[str, float]:
        """Return base costs for all product types."""
        return {pt: self.get_base_cost(pt, print_provider_id) for pt in _BLUEPRINT_MAP}

    def create_product(
        self,
        product_type: str,
        title: str,
        description: str,
        image_url: str,
        retail_price: float,
        print_provider_id: int = 99,
    ) -> str:
        blueprint_id = _BLUEPRINT_MAP.get(product_type)
        if not blueprint_id:
            raise ValueError(f"Unknown product type for Printify: '{product_type}'")

        variants_data = self._request(
            "GET",
            f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json",
        )
        variants = [
            {"id": v["id"], "price": int(retail_price * 100), "is_enabled": True}
            for v in variants_data.get("data", [])[:20]
        ]

        payload = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": variants,
            "print_areas": [
                {
                    "variant_ids": [v["id"] for v in variants_data.get("data", [])[:20]],
                    "placeholders": [
                        {
                            "position": "front",
                            "images": [{"id": "", "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}],
                        }
                    ],
                }
            ],
        }

        result = self._request("POST", f"/shops/{settings.PRINTIFY_SHOP_ID}/products.json", json=payload)
        product_id = result.get("id", "")
        if not product_id:
            raise PrintifyProductError(f"Printify create_product returned no ID: {result}")
        logger.info("printify.create_product product_id=%s type=%s title=%r", product_id, product_type, title)
        return str(product_id)

    def delete_product(self, printify_product_id: str) -> None:
        try:
            self._request("DELETE", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json")
            logger.info("printify.delete_product product_id=%s", printify_product_id)
        except Exception as e:
            logger.error("printify.delete_product failed product_id=%s error=%s", printify_product_id, e)

    def generate_mockups(self, printify_product_id: str, design_id: str | None = None) -> dict:
        """
        Fetch mockup URLs from Printify, upload to Supabase if design_id given.
        Returns {front: url, back: url} dict (Supabase URLs when design_id provided).
        """
        try:
            result = self._request(
                "GET",
                f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json",
            )
            images = result.get("images", [])
            mockup_urls: dict[str, str] = {}

            for img in images:
                position = img.get("position", "front")
                src = img.get("src", "")
                if position in ("front", "back") and src:
                    if design_id:
                        # Download and re-upload to our Supabase bucket for CDN control
                        with httpx.Client(timeout=_TIMEOUT) as http:
                            r = http.get(src)
                            r.raise_for_status()
                        path = storage.mockup_path(design_id, "tshirt", position)
                        url = storage.upload(path, r.content, "image/png")
                        mockup_urls[position] = url
                    else:
                        mockup_urls[position] = src

            logger.info("printify.generate_mockups product_id=%s positions=%s", printify_product_id, list(mockup_urls))
            return mockup_urls
        except Exception as e:
            logger.error("printify.generate_mockups failed product_id=%s error=%s", printify_product_id, e)
            raise PrintifyMockupError(f"Mockup generation failed for {printify_product_id}: {e}") from e

    def health_check(self) -> dict:
        try:
            start = time.monotonic()
            result = self._request("GET", "/shops.json")
            ms = round((time.monotonic() - start) * 1000)
            shops = result if isinstance(result, list) else result.get("data", result)
            shop_ids = [s.get("id") for s in shops] if isinstance(shops, list) else []
            target_id = int(settings.PRINTIFY_SHOP_ID) if settings.PRINTIFY_SHOP_ID else 0
            ok = target_id in shop_ids
            return {"service": "printify", "ok": ok, "ms": ms, "shop_found": ok, "shops": len(shop_ids)}
        except PrintifyAuthError as e:
            return {"service": "printify", "ok": False, "error": "auth_failed", "detail": str(e)}
        except Exception as e:
            logger.warning("printify.health_check failed error=%s", e)
            return {"service": "printify", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_printify_service() -> PrintifyService:
    return PrintifyService()


# ─── Module-level aliases for backwards compatibility ─────────────────────────

_svc: PrintifyService | None = None


def _get() -> PrintifyService:
    global _svc
    if _svc is None:
        _svc = PrintifyService()
    return _svc


def get_blueprint_variants(product_type: str) -> list[dict]:
    return _get().get_blueprint_variants(product_type)


def get_base_cost(product_type: str, print_provider_id: int = 99) -> float:
    return _get().get_base_cost(product_type, print_provider_id)


def create_product(
    product_type: str,
    title: str,
    description: str,
    image_url: str,
    retail_price: float,
    print_provider_id: int = 99,
) -> str:
    return _get().create_product(product_type, title, description, image_url, retail_price, print_provider_id)


def delete_product(printify_product_id: str) -> None:
    _get().delete_product(printify_product_id)


def generate_mockups(printify_product_id: str) -> dict:
    return _get().generate_mockups(printify_product_id)
