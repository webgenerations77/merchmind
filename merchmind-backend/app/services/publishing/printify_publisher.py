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
    "mug": 68,
    "hat": 1447,
    "phone_case": 269,
    "sticker": 400,
    "poster": 282,
}

_FALLBACK_BASE_COSTS = {
    "tshirt": 8.50,
    "mug": 6.00,
    "hat": 10.00,
    "phone_case": 8.00,
    "sticker": 2.50,
    "poster": 12.00,
}

_DUAL_PRINT_SURCHARGE = {
    "tshirt": 2.50,
    "hat": 3.00,
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
        return data.get("variants", data.get("data", []))

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

    def upload_image(self, image_url: str, file_name: str = "design.png") -> str:
        """Upload an image to Printify via URL. Returns the Printify image ID."""
        result = self._request(
            "POST",
            "/uploads/images.json",
            json={"file_name": file_name, "url": image_url},
        )
        image_id = result.get("id", "")
        if not image_id:
            raise PrintifyError(f"Printify upload returned no ID: {result}")
        logger.info("printify.upload_image id=%s file=%s", image_id, file_name)
        return str(image_id)

    def create_product(
        self,
        product_type: str,
        title: str,
        description: str,
        image_url: str,
        retail_price: float,
        print_provider_id: int = 99,
        back_logo_url: str | None = None,
    ) -> str:
        blueprint_id = _BLUEPRINT_MAP.get(product_type)
        if not blueprint_id:
            raise ValueError(f"Unknown product type for Printify: '{product_type}'")

        printify_image_id = self.upload_image(image_url, f"{product_type}_design.png")

        all_variants = self.get_blueprint_variants(product_type, print_provider_id)
        variants = [
            {"id": v["id"], "price": int(retail_price * 100), "is_enabled": True}
            for v in all_variants[:20]
        ]

        placeholders = [
            {
                "position": "front",
                "images": [{"id": printify_image_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}],
            }
        ]

        if back_logo_url:
            try:
                back_image_id = self.upload_image(back_logo_url, f"{product_type}_back_logo.png")
                placeholders.append({
                    "position": "back",
                    "images": [{"id": back_image_id, "x": 0.5, "y": 0.3, "scale": 0.5, "angle": 0}],
                })
                logger.info("printify.create_product adding back logo type=%s", product_type)
            except Exception as e:
                logger.warning("printify.create_product back logo upload failed type=%s error=%s", product_type, e)

        payload = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": variants,
            "print_areas": [
                {
                    "variant_ids": [v["id"] for v in all_variants[:20]],
                    "placeholders": placeholders,
                }
            ],
        }

        result = self._request("POST", f"/shops/{settings.PRINTIFY_SHOP_ID}/products.json", json=payload)
        product_id = result.get("id", "")
        if not product_id:
            raise PrintifyProductError(f"Printify create_product returned no ID: {result}")
        logger.info("printify.create_product product_id=%s type=%s title=%r back_logo=%s", product_id, product_type, title, bool(back_logo_url))
        return str(product_id)

    def publish_product(self, printify_product_id: str) -> None:
        """Publish a Printify product to the connected Shopify store."""
        self._request(
            "POST",
            f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}/publish.json",
            json={
                "title": True,
                "description": True,
                "images": True,
                "variants": True,
                "tags": True,
                "keyFeatures": True,
                "shipping_template": True,
            },
        )
        logger.info("printify.publish_product product_id=%s", printify_product_id)

    def delete_product(self, printify_product_id: str) -> None:
        try:
            self._request("DELETE", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json")
            logger.info("printify.delete_product product_id=%s", printify_product_id)
        except Exception as e:
            logger.error("printify.delete_product failed product_id=%s error=%s", printify_product_id, e)

    def generate_mockups(self, printify_product_id: str, design_id: str | None = None) -> dict:
        """
        Fetch mockup URLs from Printify after a short delay for rendering.
        Returns {front: url} dict using Printify CDN URLs directly.
        """
        try:
            time.sleep(5)
            result = self._request(
                "GET",
                f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json",
            )
            images = result.get("images", [])
            front_url = ""
            back_url = ""
            for img in images:
                position = img.get("position", "front")
                src = img.get("src", "")
                if position == "front" and src and not front_url:
                    front_url = src
                elif position == "back" and src and not back_url:
                    back_url = src

            mockup_urls: dict[str, str] = {}
            if front_url:
                mockup_urls["front"] = front_url
            if back_url:
                mockup_urls["back"] = back_url

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
    back_logo_url: str | None = None,
) -> str:
    return _get().create_product(product_type, title, description, image_url, retail_price, print_provider_id, back_logo_url)


def delete_product(printify_product_id: str) -> None:
    _get().delete_product(printify_product_id)


def generate_mockups(printify_product_id: str) -> dict:
    return _get().generate_mockups(printify_product_id)
