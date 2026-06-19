"""
Instagram Graph API service for posting content and fetching insights.
Auto-refreshes long-lived tokens 24 hours before expiry.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import httpx

from app.config import settings
from app.utils.exceptions import (
    InstagramAuthError,
    InstagramError,
    InstagramPostError,
    InstagramRateLimitError,
    InstagramTokenExpiredError,
)
from app.utils.utm_builder import instagram_url

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v19.0"
_TIMEOUT = 30
_TOKEN_REFRESH_BUFFER_HOURS = 24


class InstagramService:
    def __init__(self) -> None:
        self._token = settings.INSTAGRAM_ACCESS_TOKEN
        self._account_id = settings.INSTAGRAM_ACCOUNT_ID
        self._token_expires_at: datetime | None = None

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: dict | None = None, params: dict | None = None) -> dict:
        return self._request("POST", path, json=json, params=params)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        self._maybe_refresh_token()
        url = f"{_GRAPH_BASE}/{path}"
        params = kwargs.pop("params", {}) or {}
        params["access_token"] = self._token
        start = time.monotonic()
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                response = client.request(method, url, params=params, **kwargs)
            elapsed = round((time.monotonic() - start) * 1000)
            logger.info("instagram.request method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)
            data = response.json()
            if response.status_code == 429:
                raise InstagramRateLimitError(f"Instagram rate limited on {path}")
            if response.status_code in (401, 403):
                error_code = data.get("error", {}).get("code", 0)
                if error_code in (190, 102):
                    raise InstagramTokenExpiredError(f"Instagram token expired: {data.get('error', {}).get('message')}")
                raise InstagramAuthError(f"Instagram auth error on {path}: {data}")
            response.raise_for_status()
            return data
        except (InstagramRateLimitError, InstagramAuthError, InstagramTokenExpiredError):
            raise
        except Exception as e:
            raise InstagramError(f"Instagram request failed on {path}: {e}") from e

    def _maybe_refresh_token(self) -> None:
        if not self._token_expires_at:
            return
        refresh_threshold = self._token_expires_at - timedelta(hours=_TOKEN_REFRESH_BUFFER_HOURS)
        if datetime.now(tz=timezone.utc) < refresh_threshold:
            return
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.get(
                    f"{_GRAPH_BASE}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": getattr(settings, "INSTAGRAM_APP_ID", ""),
                        "client_secret": getattr(settings, "INSTAGRAM_APP_SECRET", ""),
                        "fb_exchange_token": self._token,
                    },
                )
                r.raise_for_status()
                data = r.json()
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 5184000)
            self._token_expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
            logger.info("instagram.token_refreshed expires_at=%s", self._token_expires_at.isoformat())
        except Exception as e:
            logger.error("instagram.token_refresh failed error=%s — posting may fail", e)

    def schedule_post(
        self,
        image_url: str,
        caption: str,
        product_url: str,
        campaign: str,
        scheduled_at: datetime | None = None,
    ) -> str:
        """
        Create a container + publish immediately (or schedule if scheduled_at given).
        Returns the media ID.
        """
        tagged_url = instagram_url(product_url, campaign, content="post")
        full_caption = f"{caption}\n\n🔗 {tagged_url}"

        container = self._post(
            f"{self._account_id}/media",
            params={
                "image_url": image_url,
                "caption": full_caption,
                "media_type": "IMAGE",
            },
        )
        container_id = container.get("id")
        if not container_id:
            raise InstagramPostError(f"Instagram media container creation failed: {container}")

        if scheduled_at:
            publish_time = int(scheduled_at.timestamp())
            publish_params = {
                "creation_id": container_id,
                "scheduled_publish_time": publish_time,
                "status": "SCHEDULED",
            }
        else:
            publish_params = {"creation_id": container_id}

        result = self._post(f"{self._account_id}/media_publish", params=publish_params)
        media_id = result.get("id", "")
        logger.info("instagram.schedule_post media_id=%s campaign=%s", media_id, campaign)
        return media_id

    def get_insights(self, media_id: str) -> dict:
        """Fetch engagement metrics for a specific post."""
        try:
            data = self._get(
                f"{media_id}/insights",
                params={"metric": "impressions,reach,likes,comments,shares,saved"},
            )
            metrics = {}
            for item in data.get("data", []):
                metrics[item["name"]] = item.get("value", 0)
            return metrics
        except Exception as e:
            logger.error("instagram.get_insights failed media_id=%s error=%s", media_id, e)
            return {}

    def get_account_insights(self, period: str = "week") -> dict:
        """Fetch account-level insights."""
        try:
            data = self._get(
                f"{self._account_id}/insights",
                params={
                    "metric": "impressions,reach,profile_views,follower_count",
                    "period": period,
                },
            )
            return {item["name"]: item.get("values", [{}])[-1].get("value", 0) for item in data.get("data", [])}
        except Exception as e:
            logger.error("instagram.get_account_insights failed error=%s", e)
            return {}

    def health_check(self) -> dict:
        try:
            start = time.monotonic()
            data = self._get(f"{self._account_id}", params={"fields": "id,name"})
            ms = round((time.monotonic() - start) * 1000)
            ok = bool(data.get("id"))
            return {"service": "instagram", "ok": ok, "ms": ms}
        except InstagramTokenExpiredError as e:
            return {"service": "instagram", "ok": False, "error": "token_expired", "detail": str(e)}
        except InstagramAuthError as e:
            return {"service": "instagram", "ok": False, "error": "auth_failed", "detail": str(e)}
        except Exception as e:
            logger.warning("instagram.health_check failed error=%s", e)
            return {"service": "instagram", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_instagram_service() -> InstagramService:
    return InstagramService()
