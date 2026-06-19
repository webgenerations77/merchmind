"""
TikTok Content Posting API service.
Gracefully degrades when the account API tier is insufficient.
Never crashes the pipeline — always returns an empty result with a logged warning.
"""
import logging
import time
from datetime import datetime
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.exceptions import TikTokAPITierError, TikTokAuthError, TikTokError, TikTokRateLimitError
from app.utils.utm_builder import tiktok_url

logger = logging.getLogger(__name__)

_BASE_URL = "https://open.tiktokapis.com/v2"
_TIMEOUT = 30
_TIER_ERROR_CODES = {4000, 4001, 4002, 10000, 10002, 10005}
_TIER_WARNING = (
    "TikTok API call skipped — account does not have Content Posting API access. "
    "Apply for Content Posting API in the TikTok Developer portal to enable TikTok posting."
)


class TikTokService:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{_BASE_URL}{path}"
        start = time.monotonic()
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                response = client.request(method, url, headers=self._headers(), **kwargs)
            elapsed = round((time.monotonic() - start) * 1000)
            data = response.json()
            logger.info("tiktok.request method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)

            error_code = data.get("error", {}).get("code", 0) if isinstance(data.get("error"), dict) else 0
            if response.status_code in (401, 403) or error_code in _TIER_ERROR_CODES:
                raise TikTokAPITierError(f"TikTok tier/auth error {response.status_code} code={error_code}")
            if response.status_code == 429:
                raise TikTokRateLimitError(f"TikTok rate limited on {path}")
            response.raise_for_status()
            return data
        except (TikTokAPITierError, TikTokRateLimitError):
            raise
        except Exception as e:
            raise TikTokError(f"TikTok request failed on {path}: {e}") from e

    def post_video(
        self,
        video_url: str,
        caption: str,
        product_url: str,
        campaign: str,
        scheduled_at: datetime | None = None,
    ) -> str | None:
        """
        Upload a video to TikTok. Returns post ID or None on tier/auth failure.
        """
        if not settings.TIKTOK_ACCESS_TOKEN:
            logger.info("tiktok.post_video skipped — no access token configured")
            return None
        try:
            tagged_caption = f"{caption}\n\n{tiktok_url(product_url, campaign, content='video')}"
            payload: dict = {
                "post_info": {
                    "title": tagged_caption[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                },
            }
            if scheduled_at:
                payload["post_info"]["scheduled_publish_time"] = int(scheduled_at.timestamp())

            data = self._request("POST", "/post/publish/video/init/", json=payload)
            post_id = data.get("data", {}).get("publish_id", "")
            logger.info("tiktok.post_video publish_id=%s campaign=%s", post_id, campaign)
            return post_id
        except TikTokAPITierError:
            logger.warning("tiktok.post_video %s", _TIER_WARNING)
            return None
        except TikTokRateLimitError:
            logger.warning("tiktok.post_video rate limited campaign=%s", campaign)
            return None
        except Exception as e:
            logger.warning("tiktok.post_video failed campaign=%s error=%s", campaign, e)
            return None

    def post_photo(
        self,
        image_url: str,
        caption: str,
        product_url: str,
        campaign: str,
    ) -> str | None:
        """
        Post a photo carousel to TikTok. Returns post ID or None on failure.
        """
        if not settings.TIKTOK_ACCESS_TOKEN:
            return None
        try:
            tagged_caption = f"{caption}\n\n{tiktok_url(product_url, campaign, content='photo')}"
            data = self._request(
                "POST",
                "/post/publish/content/init/",
                json={
                    "post_info": {
                        "title": tagged_caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "photo_cover_index": 0,
                        "photo_images": [image_url],
                    },
                    "post_mode": "DIRECT_POST",
                    "media_type": "PHOTO",
                },
            )
            post_id = data.get("data", {}).get("publish_id", "")
            logger.info("tiktok.post_photo publish_id=%s campaign=%s", post_id, campaign)
            return post_id
        except TikTokAPITierError:
            logger.warning("tiktok.post_photo %s", _TIER_WARNING)
            return None
        except Exception as e:
            logger.warning("tiktok.post_photo failed campaign=%s error=%s", campaign, e)
            return None

    def get_video_metrics(self, video_id: str) -> dict:
        """Fetch metrics for a published video. Returns empty dict on failure."""
        try:
            data = self._request(
                "POST",
                "/video/query/",
                json={
                    "filters": {"video_ids": [video_id]},
                    "fields": ["id", "like_count", "comment_count", "share_count", "view_count"],
                },
            )
            videos = data.get("data", {}).get("videos", [])
            return videos[0] if videos else {}
        except TikTokAPITierError:
            logger.warning("tiktok.get_video_metrics %s", _TIER_WARNING)
            return {}
        except Exception as e:
            logger.warning("tiktok.get_video_metrics failed video_id=%s error=%s", video_id, e)
            return {}

    def health_check(self) -> dict:
        if not settings.TIKTOK_ACCESS_TOKEN:
            return {"service": "tiktok", "ok": False, "error": "no_token", "degraded": True}
        try:
            start = time.monotonic()
            data = self._request("GET", "/user/info/", params={"fields": "open_id,display_name"})
            ms = round((time.monotonic() - start) * 1000)
            ok = bool(data.get("data", {}).get("user", {}).get("open_id"))
            return {"service": "tiktok", "ok": ok, "ms": ms}
        except TikTokAPITierError:
            return {"service": "tiktok", "ok": False, "error": "tier_insufficient", "degraded": True}
        except Exception as e:
            logger.warning("tiktok.health_check failed error=%s", e)
            return {"service": "tiktok", "ok": False, "error": str(e), "degraded": True}


@lru_cache(maxsize=1)
def get_tiktok_service() -> TikTokService:
    return TikTokService()
