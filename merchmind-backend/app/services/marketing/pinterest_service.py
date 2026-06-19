"""
Pinterest API v5 service.
Auto-refreshes OAuth tokens 24h before expiry.
Staggers pin creation 1 hour apart to avoid spam detection.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.exceptions import (
    PinterestAuthError,
    PinterestError,
    PinterestPinError,
    PinterestRateLimitError,
    PinterestTokenExpiredError,
)
from app.utils.utm_builder import pinterest_url

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.pinterest.com/v5"
_TIMEOUT = 30
_TOKEN_REFRESH_BUFFER_HOURS = 24
_PIN_STAGGER_SECONDS = 3600


class PinterestService:
    def __init__(self) -> None:
        self._token = settings.PINTEREST_ACCESS_TOKEN
        self._token_expires_at: datetime | None = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: dict | None = None) -> dict:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        self._maybe_refresh_token()
        url = f"{_BASE_URL}/{path.lstrip('/')}"
        start = time.monotonic()
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                response = client.request(method, url, headers=self._headers(), **kwargs)
            elapsed = round((time.monotonic() - start) * 1000)
            logger.info("pinterest.request method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)
            if response.status_code == 429:
                raise PinterestRateLimitError(f"Pinterest rate limited on {path}")
            if response.status_code == 401:
                raise PinterestTokenExpiredError(f"Pinterest token expired on {path}")
            if response.status_code == 403:
                raise PinterestAuthError(f"Pinterest auth error on {path}")
            response.raise_for_status()
            return response.json()
        except (PinterestRateLimitError, PinterestAuthError, PinterestTokenExpiredError):
            raise
        except Exception as e:
            raise PinterestError(f"Pinterest request failed on {path}: {e}") from e

    def _maybe_refresh_token(self) -> None:
        if not self._token_expires_at:
            return
        refresh_threshold = self._token_expires_at - timedelta(hours=_TOKEN_REFRESH_BUFFER_HOURS)
        if datetime.now(tz=timezone.utc) < refresh_threshold:
            return
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.post(
                    "https://api.pinterest.com/v5/oauth/token",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": getattr(settings, "PINTEREST_REFRESH_TOKEN", ""),
                        "client_id": getattr(settings, "PINTEREST_APP_ID", ""),
                        "client_secret": getattr(settings, "PINTEREST_APP_SECRET", ""),
                    },
                )
                r.raise_for_status()
                data = r.json()
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 2592000)
            self._token_expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
            logger.info("pinterest.token_refreshed expires_at=%s", self._token_expires_at.isoformat())
        except Exception as e:
            logger.error("pinterest.token_refresh failed error=%s — posting may fail", e)

    def ensure_board_exists(self, board_name: str) -> str:
        """Return board ID, creating it if it doesn't exist."""
        try:
            data = self._get("boards", params={"page_size": 100})
            for board in data.get("items", []):
                if board["name"].lower() == board_name.lower():
                    return board["id"]
        except Exception as e:
            logger.warning("pinterest.ensure_board_exists list failed error=%s", e)

        result = self._post("boards", json={"name": board_name, "privacy": "PUBLIC"})
        board_id = result.get("id", "")
        logger.info("pinterest.ensure_board_exists created board_id=%s name=%r", board_id, board_name)
        return board_id

    def create_pin(
        self,
        board_id: str,
        title: str,
        description: str,
        image_url: str,
        product_url: str,
        campaign: str,
        content: str = "pin",
    ) -> str:
        """Create a single pin. Returns pin ID."""
        tagged_link = pinterest_url(product_url, campaign, content=content)
        payload = {
            "board_id": board_id,
            "title": title[:100],
            "description": description[:500],
            "link": tagged_link,
            "media_source": {
                "source_type": "image_url",
                "url": image_url,
            },
        }
        result = self._post("pins", json=payload)
        pin_id = result.get("id", "")
        logger.info("pinterest.create_pin pin_id=%s board_id=%s campaign=%s", pin_id, board_id, campaign)
        return pin_id

    async def create_pin_variants(
        self,
        board_id: str,
        title: str,
        description: str,
        image_urls: list[str],
        product_url: str,
        campaign: str,
    ) -> list[str]:
        """
        Create one pin per image URL, staggered 1 hour apart.
        Returns list of pin IDs (skips failures).
        """
        pin_ids = []
        for i, image_url in enumerate(image_urls):
            if i > 0:
                logger.info("pinterest.create_pin_variants stagger wait=%ds", _PIN_STAGGER_SECONDS)
                await asyncio.sleep(_PIN_STAGGER_SECONDS)
            try:
                pin_id = self.create_pin(
                    board_id=board_id,
                    title=title,
                    description=description,
                    image_url=image_url,
                    product_url=product_url,
                    campaign=campaign,
                    content=f"pin-{i + 1}",
                )
                pin_ids.append(pin_id)
            except Exception as e:
                logger.warning("pinterest.create_pin_variants variant=%d failed error=%s", i, e)
        return pin_ids

    def get_pin_analytics(self, pin_id: str, start_date: str, end_date: str) -> dict:
        """Fetch analytics for a pin. Returns empty dict on failure."""
        try:
            data = self._get(
                f"pins/{pin_id}/analytics",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "metric_types": "IMPRESSION,CLICK_ON_PIN,SAVE",
                },
            )
            return data.get("all", {}).get("daily_metrics", {})
        except Exception as e:
            logger.error("pinterest.get_pin_analytics failed pin_id=%s error=%s", pin_id, e)
            return {}

    def health_check(self) -> dict:
        try:
            start = time.monotonic()
            data = self._get("user_account")
            ms = round((time.monotonic() - start) * 1000)
            ok = bool(data.get("username"))
            return {"service": "pinterest", "ok": ok, "ms": ms}
        except PinterestTokenExpiredError as e:
            return {"service": "pinterest", "ok": False, "error": "token_expired", "detail": str(e)}
        except PinterestAuthError as e:
            return {"service": "pinterest", "ok": False, "error": "auth_failed", "detail": str(e)}
        except Exception as e:
            logger.warning("pinterest.health_check failed error=%s", e)
            return {"service": "pinterest", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_pinterest_service() -> PinterestService:
    return PinterestService()
