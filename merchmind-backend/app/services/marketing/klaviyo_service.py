"""
Klaviyo email marketing service.
Creates campaigns, manages subscribers, and builds product launch email HTML.
All product links carry UTM tracking.
"""
import logging
import time
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.exceptions import KlaviyoAuthError, KlaviyoCampaignError, KlaviyoError, KlaviyoRateLimitError
from app.utils.utm_builder import email_url

logger = logging.getLogger(__name__)

_BASE_URL = "https://a.klaviyo.com/api"
_TIMEOUT = 30
_MAX_RETRIES = 3


class KlaviyoService:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Klaviyo-API-Key {settings.KLAVIYO_API_KEY}",
            "Content-Type": "application/json",
            "revision": "2024-02-15",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{_BASE_URL}/{path.lstrip('/')}"
        for attempt in range(_MAX_RETRIES):
            start = time.monotonic()
            try:
                with httpx.Client(timeout=_TIMEOUT) as client:
                    response = client.request(method, url, headers=self._headers(), **kwargs)
                elapsed = round((time.monotonic() - start) * 1000)
                logger.info("klaviyo.request method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)
                if response.status_code == 401:
                    raise KlaviyoAuthError(f"Klaviyo auth failed on {path}")
                if response.status_code == 429:
                    wait = float(response.headers.get("Retry-After", 2 ** attempt * 5))
                    logger.warning("klaviyo.rate_limit wait=%.1fs attempt=%d", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json() if response.content else {}
            except (KlaviyoAuthError, KlaviyoRateLimitError):
                raise
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise KlaviyoError(f"Klaviyo request failed on {path}: {e}") from e
        raise KlaviyoError("Klaviyo: max retries exceeded")

    def add_subscriber(self, email: str, first_name: str = "", properties: dict | None = None) -> str:
        """Add/update a subscriber in the default list. Returns profile ID."""
        payload = {
            "data": {
                "type": "profile",
                "attributes": {
                    "email": email,
                    "first_name": first_name,
                    **(properties or {}),
                },
            }
        }
        data = self._request("POST", "profiles/", json=payload)
        profile_id = data.get("data", {}).get("id", "")

        if profile_id and settings.KLAVIYO_LIST_ID:
            self._request(
                "POST",
                f"lists/{settings.KLAVIYO_LIST_ID}/relationships/profiles/",
                json={"data": [{"type": "profile", "id": profile_id}]},
            )
        logger.info("klaviyo.add_subscriber email=%s profile_id=%s", email, profile_id)
        return profile_id

    def remove_subscriber(self, email: str) -> None:
        """Unsubscribe a profile from the default list."""
        try:
            profiles = self._request("GET", f"profiles/?filter=equals(email,'{email}')")
            profile_id = profiles.get("data", [{}])[0].get("id", "")
            if not profile_id:
                return
            if settings.KLAVIYO_LIST_ID:
                self._request(
                    "DELETE",
                    f"lists/{settings.KLAVIYO_LIST_ID}/relationships/profiles/",
                    json={"data": [{"type": "profile", "id": profile_id}]},
                )
            logger.info("klaviyo.remove_subscriber email=%s", email)
        except Exception as e:
            logger.error("klaviyo.remove_subscriber failed email=%s error=%s", email, e)

    def create_campaign(
        self,
        subject: str,
        preview_text: str,
        html_body: str,
        from_email: str = "hello@merchmind.com",
        from_name: str = "MerchMind",
        list_id: str | None = None,
    ) -> str:
        """Create and send a Klaviyo email campaign. Returns campaign ID."""
        target_list = list_id or settings.KLAVIYO_LIST_ID
        if not target_list:
            raise KlaviyoCampaignError("No Klaviyo list ID configured")

        # Create campaign
        campaign_data = self._request(
            "POST",
            "campaigns/",
            json={
                "data": {
                    "type": "campaign",
                    "attributes": {
                        "name": subject[:200],
                        "audiences": {"included": [target_list]},
                        "send_strategy": {"method": "immediate"},
                        "campaign-messages": {
                            "data": [
                                {
                                    "type": "campaign-message",
                                    "attributes": {
                                        "definition": {
                                            "subject": subject,
                                            "preview_text": preview_text,
                                            "from_email": from_email,
                                            "from_name": from_name,
                                        },
                                        "content": {"html": html_body},
                                    },
                                }
                            ]
                        },
                    },
                }
            },
        )
        campaign_id = campaign_data.get("data", {}).get("id", "")
        if not campaign_id:
            raise KlaviyoCampaignError(f"Klaviyo campaign creation failed: {campaign_data}")

        # Send immediately
        self._request("POST", f"campaigns/{campaign_id}/campaign-send-job/", json={"data": {"type": "campaign-send-job"}})
        logger.info("klaviyo.create_campaign campaign_id=%s subject=%r", campaign_id, subject)
        return campaign_id

    def get_campaign_metrics(self, campaign_id: str) -> dict:
        """Fetch open rate, click rate, conversion rate for a campaign."""
        try:
            data = self._request("GET", f"campaigns/{campaign_id}/")
            attrs = data.get("data", {}).get("attributes", {})
            return {
                "sends": attrs.get("send_time"),
                "status": attrs.get("status"),
            }
        except Exception as e:
            logger.error("klaviyo.get_campaign_metrics failed campaign_id=%s error=%s", campaign_id, e)
            return {}

    def build_product_launch_email(
        self,
        design_title: str,
        tagline: str,
        product_url: str,
        image_url: str,
        price: float,
        campaign: str,
        niche: str = "",
    ) -> str:
        """Return HTML for a product launch email with UTM-tracked links."""
        cta_url = email_url(product_url, campaign, content="cta_button")
        image_link_url = email_url(product_url, campaign, content="email_image")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{design_title}</title>
</head>
<body style="margin:0;padding:0;background-color:#0A0A0A;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background-color:#141414;">
  <tr>
    <td style="padding:32px 24px;text-align:center;">
      <p style="color:#9CA3AF;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin:0 0 24px;">
        {"New Drop · " + niche if niche else "New Drop"}
      </p>
      <a href="{image_link_url}" style="display:block;">
        <img src="{image_url}" alt="{design_title}" style="width:100%;border-radius:12px;display:block;">
      </a>
    </td>
  </tr>
  <tr>
    <td style="padding:0 24px 32px;text-align:center;">
      <h1 style="color:#F9FAFB;font-size:28px;font-weight:700;margin:0 0 12px;">{design_title}</h1>
      <p style="color:#9CA3AF;font-size:16px;line-height:1.6;margin:0 0 8px;">{tagline}</p>
      <p style="color:#6366F1;font-size:20px;font-weight:600;margin:16px 0 28px;">${price:.2f}</p>
      <a href="{cta_url}" style="display:inline-block;background-color:#6366F1;color:#ffffff;
         text-decoration:none;padding:14px 36px;border-radius:8px;font-size:16px;font-weight:600;">
        Shop Now
      </a>
    </td>
  </tr>
  <tr>
    <td style="padding:24px;border-top:1px solid #2A2A2A;text-align:center;">
      <p style="color:#6B7280;font-size:12px;margin:0;">
        You're receiving this because you subscribed to MerchMind drops.<br>
        <a href="{{{{unsubscribe_url}}}}" style="color:#6366F1;text-decoration:none;">Unsubscribe</a>
      </p>
    </td>
  </tr>
</table>
</body>
</html>"""

    def health_check(self) -> dict:
        if not settings.KLAVIYO_API_KEY:
            return {"service": "klaviyo", "ok": False, "error": "no_api_key"}
        try:
            start = time.monotonic()
            data = self._request("GET", "accounts/")
            ms = round((time.monotonic() - start) * 1000)
            ok = bool(data.get("data"))
            return {"service": "klaviyo", "ok": ok, "ms": ms}
        except KlaviyoAuthError as e:
            return {"service": "klaviyo", "ok": False, "error": "auth_failed", "detail": str(e)}
        except Exception as e:
            logger.warning("klaviyo.health_check failed error=%s", e)
            return {"service": "klaviyo", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_klaviyo_service() -> KlaviyoService:
    return KlaviyoService()
