"""
Placeit lifestyle mockup service.
Non-critical — failures are logged and swallowed; never block the publishing pipeline.
"""
import asyncio
import logging
import time
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.exceptions import PlaceitAuthError, PlaceitError, PlaceitRenderError, PlaceitTimeoutError
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_BASE_URL = "https://placeit.net/api/v2"
_TIMEOUT = 30
_POLL_INTERVAL = 3
_MAX_WAIT = 90


class PlaceitService:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.PLACEIT_API_KEY}",
            "Content-Type": "application/json",
        }

    async def render_mockup(
        self,
        template_id: str,
        design_url: str,
        design_id: str,
        label: str = "lifestyle",
    ) -> str | None:
        """
        Submit a render job, poll until complete, upload to Supabase.
        Returns public URL or None if Placeit is unavailable.
        Non-critical: logs errors and returns None rather than raising.
        """
        if not settings.PLACEIT_API_KEY:
            logger.info("placeit.render_mockup skipped — no API key configured")
            return None
        try:
            job_id = await self._submit(template_id, design_url)
            url = await self._poll(job_id)
            return await self._upload(url, design_id, label)
        except PlaceitAuthError:
            logger.warning("placeit.render_mockup auth failed template_id=%s", template_id)
            return None
        except PlaceitTimeoutError:
            logger.warning("placeit.render_mockup timed out template_id=%s", template_id)
            return None
        except Exception as e:
            logger.warning("placeit.render_mockup non-critical failure template_id=%s error=%s", template_id, e)
            return None

    async def _submit(self, template_id: str, design_url: str) -> str:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            start = time.monotonic()
            r = await client.post(
                f"{_BASE_URL}/renders",
                headers=self._headers(),
                json={"template_id": template_id, "design_url": design_url},
            )
            elapsed = round((time.monotonic() - start) * 1000)
            logger.info("placeit.submit status=%d ms=%d", r.status_code, elapsed)
            if r.status_code == 401:
                raise PlaceitAuthError("Placeit auth failed")
            r.raise_for_status()
            return r.json()["id"]

    async def _poll(self, job_id: str) -> str:
        deadline = time.monotonic() + _MAX_WAIT
        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL)
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(f"{_BASE_URL}/renders/{job_id}", headers=self._headers())
                r.raise_for_status()
                data = r.json()
            status = data.get("status")
            if status == "completed":
                return data["result_url"]
            if status in ("failed", "error"):
                raise PlaceitRenderError(f"Placeit render {job_id} failed: {data.get('error')}")
        raise PlaceitTimeoutError(f"Placeit render {job_id} timed out after {_MAX_WAIT}s")

    async def _upload(self, render_url: str, design_id: str, label: str) -> str:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(render_url)
            r.raise_for_status()
        path = f"designs/{design_id}/mockups/lifestyle/{label}.jpg"
        return storage.upload(path, r.content, "image/jpeg")

    def health_check(self) -> dict:
        if not settings.PLACEIT_API_KEY:
            return {"service": "placeit", "ok": False, "error": "no_api_key", "critical": False}
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(f"{_BASE_URL}/templates", headers=self._headers(), params={"limit": 1})
            ok = r.status_code == 200
            return {"service": "placeit", "ok": ok, "critical": False}
        except Exception as e:
            logger.warning("placeit.health_check failed error=%s", e)
            return {"service": "placeit", "ok": False, "error": str(e), "critical": False}


@lru_cache(maxsize=1)
def get_placeit_service() -> PlaceitService:
    return PlaceitService()
