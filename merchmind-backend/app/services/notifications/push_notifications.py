"""
Push notifications via Expo Push Notification Service.
"""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_TIMEOUT = 30


def send_push(
    title: str,
    body: str,
    data: dict = None,
    expo_push_token: str = None,
) -> bool:
    """
    Send a push notification via Expo.
    Returns True on success.
    """
    if not settings.EXPO_ACCESS_TOKEN:
        logger.warning("EXPO_ACCESS_TOKEN not configured — push notification skipped")
        return False

    token = expo_push_token or getattr(settings, "EXPO_PUSH_TOKEN", "")
    if not token:
        logger.warning("No Expo push token available — notification skipped")
        return False

    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(
                _EXPO_PUSH_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.EXPO_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()
            if result.get("data", {}).get("status") == "error":
                logger.error(f"Expo push error: {result}")
                return False
            logger.info(f"Push notification sent: {title}")
            return True
    except Exception as e:
        logger.error(f"Failed to send push notification '{title}': {e}")
        return False


def notify_batch_ready(batch_id: str, queued_count: int) -> bool:
    """Notify user that the weekly batch is ready for review."""
    return send_push(
        title="MerchMind Weekly Review Ready",
        body=f"Your {queued_count} products are ready for review",
        data={"type": "batch_ready", "batch_id": str(batch_id), "screen": "ReviewQueue"},
    )


def notify_publish_complete(approved_count: int) -> bool:
    """Notify user that approved products have been published."""
    return send_push(
        title="Products Published",
        body=f"{approved_count} products are now live on your Shopify store",
        data={"type": "publish_complete", "screen": "Products"},
    )


def notify_alert(alert_type: str, message: str, alert_id: str) -> bool:
    """Notify user of a system alert."""
    severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
    emoji = severity_emoji.get("warning", "⚠️")
    return send_push(
        title=f"{emoji} MerchMind Alert",
        body=message,
        data={"type": "alert", "alert_id": str(alert_id), "screen": "Alerts"},
    )
