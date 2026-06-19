"""
Email notifications via Klaviyo API.
"""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

_KLAVIYO_BASE = "https://a.klaviyo.com/api"
_TIMEOUT = 30


def _headers() -> dict:
    return {
        "Authorization": f"Klaviyo-API-Key {settings.KLAVIYO_API_KEY}",
        "Content-Type": "application/json",
        "revision": "2024-02-15",
    }


def send_batch_ready_email(
    recipient_email: str,
    batch_id: str,
    queued_count: int,
    review_url: str = "",
) -> bool:
    """
    Send 'batch ready for review' email to the store owner via Klaviyo.
    """
    if not settings.KLAVIYO_API_KEY:
        logger.warning("KLAVIYO_API_KEY not configured — email notification skipped")
        return False

    payload = {
        "data": {
            "type": "event",
            "attributes": {
                "metric": {"data": {"type": "metric", "attributes": {"name": "MerchMind Batch Ready"}}},
                "profile": {"data": {"type": "profile", "attributes": {"email": recipient_email}}},
                "properties": {
                    "batch_id": str(batch_id),
                    "queued_count": queued_count,
                    "review_url": review_url,
                },
            },
        }
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(
                f"{_KLAVIYO_BASE}/events/",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
        logger.info(f"Batch ready email sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send batch ready email to {recipient_email}: {e}")
        return False


def send_underperformer_alert_email(
    recipient_email: str,
    products: list[dict],
) -> bool:
    """Send underperformer alert email listing weak-performing products."""
    if not settings.KLAVIYO_API_KEY:
        return False
    payload = {
        "data": {
            "type": "event",
            "attributes": {
                "metric": {"data": {"type": "metric", "attributes": {"name": "MerchMind Underperformer Alert"}}},
                "profile": {"data": {"type": "profile", "attributes": {"email": recipient_email}}},
                "properties": {"underperforming_products": products},
            },
        }
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(f"{_KLAVIYO_BASE}/events/", json=payload, headers=_headers())
            response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send underperformer alert email: {e}")
        return False
