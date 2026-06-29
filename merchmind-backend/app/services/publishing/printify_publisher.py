"""
Printify API client — class-based service for creating products and generating mockups.
Uploads mockup images to Supabase Storage after generation.
"""
import io
import logging
import time
from functools import lru_cache

import httpx
from PIL import Image

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
    "hoodie": 77,
    "long_sleeve": 304,
    "mug": 68,
    "hat": 1447,
    "phone_case": 269,
    "sticker": 400,
}

_PROVIDER_MAP = {
    "tshirt": 99,
    "hoodie": 99,
    "long_sleeve": 99,
    "mug": 1,
    "hat": 410,
    "phone_case": 1,
    "sticker": 99,
}

_FALLBACK_BASE_COSTS = {
    "tshirt": 8.50,
    "hoodie": 18.00,
    "long_sleeve": 12.00,
    "mug": 6.00,
    "hat": 10.00,
    "phone_case": 8.00,
    "sticker": 2.50,
}

# Apparel scaled to 0.85 (~15% smaller print) per Drew's feedback — designs
# were filling the print area edge-to-edge; 0.85 leaves breathing room.
_SCALE_MAP = {
    "tshirt": 0.85,
    "hoodie": 0.85,
    "long_sleeve": 0.85,
    "mug": 1.0,
    "hat": 0.9,
    "phone_case": 1.0,
    "sticker": 1.2,
}

_DUAL_PRINT_SURCHARGE = {
    "tshirt": 2.50,
    "hoodie": 3.50,
    "long_sleeve": 3.00,
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

    def get_blueprint_variants(self, product_type: str, print_provider_id: int | None = None) -> list[dict]:
        blueprint_id = _BLUEPRINT_MAP.get(product_type)
        if not blueprint_id:
            raise ValueError(f"Unknown Printify product type: '{product_type}'")
        if print_provider_id is None:
            print_provider_id = _PROVIDER_MAP.get(product_type, 99)
        data = self._request(
            "GET",
            f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json",
        )
        return data.get("variants", data.get("data", []))

    def get_base_cost(self, product_type: str, print_provider_id: int | None = None) -> float:
        """Return minimum variant cost in dollars. Falls back to industry-standard costs when Printify is unavailable."""
        try:
            variants = self.get_blueprint_variants(product_type, print_provider_id)
            costs = [v.get("cost", 0) / 100.0 for v in variants if v.get("cost")]
            if costs:
                return min(costs)
        except Exception as e:
            logger.warning("printify.get_base_cost API failed, using fallback. product_type=%s error=%s", product_type, e)
        return _FALLBACK_BASE_COSTS.get(product_type, 8.00)

    def get_base_costs(self, print_provider_id: int | None = None) -> dict[str, float]:
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
        print_provider_id: int | None = None,
        back_logo_url: str | None = None,
        archetype: str | None = None,
    ) -> str:
        blueprint_id = _BLUEPRINT_MAP.get(product_type)
        if not blueprint_id:
            raise ValueError(f"Unknown product type for Printify: '{product_type}'")
        if print_provider_id is None:
            print_provider_id = _PROVIDER_MAP.get(product_type, 99)

        printify_image_id = self.upload_image(image_url, f"{product_type}_design.png")

        all_variants = self.get_blueprint_variants(product_type, print_provider_id)
        variants = [
            {"id": v["id"], "price": int(retail_price * 100), "is_enabled": True}
            for v in all_variants[:20]
        ]

        # Printify placement: x/y are normalized 0.0–1.0 within the print area.
        # y=0.5 = vertical center; y=0.35 = upper chest for text designs on tshirts.
        front_y = 0.5
        if product_type == "tshirt" and archetype in ("text_only", "typographic", "text_icon"):
            front_y = 0.35

        front_scale = _SCALE_MAP.get(product_type, 1.0)

        placeholders = [
            {
                "position": "front",
                "images": [{"id": printify_image_id, "x": 0.5, "y": front_y, "scale": front_scale, "angle": 0}],
            }
        ]

        if back_logo_url:
            try:
                back_image_id = self.upload_image(back_logo_url, f"{product_type}_back_logo.png")
                placeholders.append({
                    "position": "back",
                    "images": [{"id": back_image_id, "x": 0.5, "y": 0.15, "scale": 0.25, "angle": 0}],
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

    def unpublish_product(self, printify_product_id: str) -> None:
        """Unpublish a product from the connected Shopify store. Keeps the product in Printify."""
        self._request(
            "POST",
            f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}/unpublish.json",
        )
        logger.info("printify.unpublish_product product_id=%s", printify_product_id)

    def delete_product(self, printify_product_id: str) -> None:
        try:
            self._request("DELETE", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json")
            logger.info("printify.delete_product product_id=%s", printify_product_id)
        except Exception as e:
            logger.error("printify.delete_product failed product_id=%s error=%s", printify_product_id, e)

    @staticmethod
    def _replace_white_bg(image_bytes: bytes, bg_color: tuple = (30, 30, 35)) -> bytes:
        """Replace white/near-white background with a dark color using smooth blending."""
        from PIL import ImageChops, ImageFilter

        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        r, g, b, a = img.split()

        gray_min = ImageChops.darker(ImageChops.darker(r, g), b)
        mask = gray_min.point(lambda p: min(255, max(0, int((p - 190) * (255 / 65)))) if p >= 190 else 0)

        mask = mask.filter(ImageFilter.MaxFilter(3))
        mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))

        bg = Image.new("RGBA", img.size, (*bg_color, 255))
        result = Image.composite(bg, img, mask)

        buf = io.BytesIO()
        result.convert("RGB").save(buf, format="PNG", quality=95)
        return buf.getvalue()

    def _rehost_mockup(self, url: str, design_id: str, product_type: str, position: str) -> str:
        """Download a Printify mockup and re-upload to Supabase."""
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url)
                resp.raise_for_status()
            path = f"designs/{design_id}/mockups/{product_type}/{position}.png"
            return storage.upload(path, resp.content, "image/png")
        except Exception as e:
            logger.warning("printify.rehost_mockup failed type=%s pos=%s: %s", product_type, position, e)
            return url

    def generate_mockups(self, printify_product_id: str, design_id: str | None = None, product_type: str | None = None) -> dict:
        """
        Fetch mockup URLs from Printify after rendering delay.
        Some providers (hats, phone cases, stickers) take 30+ seconds.
        Downloads mockups, replaces white backgrounds, re-uploads to Supabase.
        Returns {front: url, back?: url} dict.
        """
        _DELAYS = [5, 10, 15]
        try:
            images = []
            for attempt, delay in enumerate(_DELAYS):
                time.sleep(delay)
                result = self._request(
                    "GET",
                    f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_product_id}.json",
                )
                images = result.get("images", [])
                if images:
                    break

            front_url = ""
            back_url = ""
            for img in images:
                position = img.get("position", "")
                src = img.get("src", "")
                if not src:
                    continue
                if position in ("front", "default") and not front_url:
                    front_url = src
                elif position == "back" and not back_url:
                    back_url = src
                elif not front_url and not position:
                    front_url = src

            mockup_urls: dict[str, str] = {}
            if front_url and design_id:
                mockup_urls["front"] = self._rehost_mockup(front_url, design_id, product_type or "unknown", "front")
            elif front_url:
                mockup_urls["front"] = front_url
            if back_url and design_id:
                mockup_urls["back"] = self._rehost_mockup(back_url, design_id, product_type or "unknown", "back")
            elif back_url:
                mockup_urls["back"] = back_url

            logger.info("printify.generate_mockups product_id=%s positions=%s attempts=%d rehosted=%s", printify_product_id, list(mockup_urls), attempt + 1, bool(design_id))
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


def get_base_cost(product_type: str, print_provider_id: int | None = None) -> float:
    return _get().get_base_cost(product_type, print_provider_id)


def create_product(
    product_type: str,
    title: str,
    description: str,
    image_url: str,
    retail_price: float,
    print_provider_id: int | None = None,
    back_logo_url: str | None = None,
    archetype: str | None = None,
) -> str:
    return _get().create_product(product_type, title, description, image_url, retail_price, print_provider_id, back_logo_url, archetype)


def delete_product(printify_product_id: str) -> None:
    _get().delete_product(printify_product_id)


def generate_mockups(printify_product_id: str, design_id: str | None = None, product_type: str | None = None) -> dict:
    return _get().generate_mockups(printify_product_id, design_id=design_id, product_type=product_type)
