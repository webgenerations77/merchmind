"""
Dynamic Mockups API client for photorealistic product mockups.
Replaces Placeit (which has no API). Falls back gracefully when
API key is missing or renders fail — never blocks the pipeline.

Setup: sign up at dynamicmockups.com, browse templates, pick one per
product type, and populate _TEMPLATE_MAP with the mockup_uuid and
smart_object_uuid from GET /mockups.
"""
import logging
import time
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_BASE_URL = "https://app.dynamicmockups.com/api/v1"
_TIMEOUT = 30

# Map product types to Dynamic Mockups template UUIDs.
# Populate these after browsing templates at dynamicmockups.com.
# Each entry needs the mockup_uuid and the smart_object uuid for the design area.
_TEMPLATE_MAP: dict[str, dict] = {
    # "tshirt": {
    #     "mockup_uuid": "...",
    #     "smart_object_uuid": "...",
    #     "label": "tshirt_front",
    # },
    # "mug": {
    #     "mockup_uuid": "...",
    #     "smart_object_uuid": "...",
    #     "label": "mug_front",
    # },
    # "hat": { ... },
    # "phone_case": { ... },
    # "poster": { ... },
    # "sticker": { ... },
}


class DynamicMockupsService:
    def _headers(self) -> dict:
        return {
            "x-api-key": settings.DYNAMIC_MOCKUPS_API_KEY,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def is_available(self) -> bool:
        return bool(settings.DYNAMIC_MOCKUPS_API_KEY) and bool(_TEMPLATE_MAP)

    def render_mockup(
        self,
        product_type: str,
        design_url: str,
        design_id: str,
    ) -> str | None:
        """
        Render a photorealistic mockup for a product type.
        Returns a Supabase public URL or None if unavailable/failed.
        Non-blocking — failures are logged and swallowed.
        """
        if not settings.DYNAMIC_MOCKUPS_API_KEY:
            return None

        template = _TEMPLATE_MAP.get(product_type)
        if not template:
            return None

        try:
            start = time.monotonic()
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.post(
                    f"{_BASE_URL}/renders",
                    headers=self._headers(),
                    json={
                        "mockup_uuid": template["mockup_uuid"],
                        "smart_objects": [
                            {
                                "uuid": template["smart_object_uuid"],
                                "asset": {"url": design_url},
                            }
                        ],
                    },
                )
            elapsed = round((time.monotonic() - start) * 1000)

            if r.status_code == 401:
                logger.warning("dynamic_mockups.render auth failed")
                return None
            r.raise_for_status()

            data = r.json().get("data", {})
            render_url = data.get("export_path")
            if not render_url:
                logger.warning("dynamic_mockups.render no export_path in response")
                return None

            logger.info(
                "dynamic_mockups.render type=%s ms=%d", product_type, elapsed
            )

            # Download rendered image and upload to Supabase
            with httpx.Client(timeout=_TIMEOUT) as client:
                img_resp = client.get(render_url)
                img_resp.raise_for_status()

            label = template.get("label", f"{product_type}_front")
            path = f"designs/{design_id}/mockups/{product_type}/{label}.png"
            return storage.upload(path, img_resp.content, "image/png")

        except Exception as e:
            logger.warning(
                "dynamic_mockups.render failed type=%s error=%s", product_type, e
            )
            return None

    def render_all(
        self,
        design_url: str,
        design_id: str,
        product_types: list[str],
    ) -> dict[str, str]:
        """Render mockups for all product types that have templates configured."""
        results = {}
        for pt in product_types:
            url = self.render_mockup(pt, design_url, design_id)
            if url:
                results[pt] = url
        return results

    def health_check(self) -> dict:
        if not settings.DYNAMIC_MOCKUPS_API_KEY:
            return {"service": "dynamic_mockups", "ok": False, "error": "no_api_key", "critical": False}
        try:
            start = time.monotonic()
            with httpx.Client(timeout=10) as client:
                r = client.get(f"{_BASE_URL}/mockups", headers=self._headers())
            ms = round((time.monotonic() - start) * 1000)
            ok = r.status_code == 200
            count = len(r.json().get("data", [])) if ok else 0
            return {"service": "dynamic_mockups", "ok": ok, "ms": ms, "templates": count, "critical": False}
        except Exception as e:
            logger.warning("dynamic_mockups.health_check failed: %s", e)
            return {"service": "dynamic_mockups", "ok": False, "error": str(e), "critical": False}


@lru_cache(maxsize=1)
def get_dynamic_mockups_service() -> DynamicMockupsService:
    return DynamicMockupsService()
