"""
Onboarding endpoints: validate API keys and check connection status.
Returns service-specific error messages so the mobile app can show actionable guidance.
"""
import logging
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)

_SERVICE_ERROR_MESSAGES = {
    "anthropic": {
        401: "Invalid Anthropic API key. Check your key at console.anthropic.com → API Keys.",
        429: "Anthropic rate limit hit. Your key is valid — retry in a moment.",
        "timeout": "Anthropic took too long to respond. Check your internet connection.",
    },
    "printify": {
        401: "Invalid Printify API key. Check your key at printify.com → My Profile → Connections.",
        429: "Printify rate limit hit. Your key is valid — retry in 60 seconds.",
        "timeout": "Printify API timed out. Try again in a moment.",
    },
    "shopify": {
        401: "Invalid Shopify access token. Re-install the MerchMind app in your Shopify admin.",
        403: "Shopify token lacks required scopes. Ensure write_products and read_orders are enabled.",
        429: "Shopify rate limit hit. Your token is valid — retry in a moment.",
        "timeout": "Shopify API timed out. Try again in a moment.",
    },
    "openai": {
        401: "Invalid OpenAI API key. Check your key at platform.openai.com → API Keys.",
        429: "OpenAI rate limit or quota exceeded. Check your usage limits at platform.openai.com.",
        "timeout": "OpenAI API timed out. Try again in a moment.",
    },
    "klaviyo": {
        401: "Invalid Klaviyo API key. Use a Private API Key from klaviyo.com → Account → API Keys.",
        429: "Klaviyo rate limit hit. Your key is valid — retry in a moment.",
        "timeout": "Klaviyo API timed out. Try again in a moment.",
    },
    "instagram": {
        401: "Instagram token expired or invalid. Re-authorize via Meta Developer portal.",
        403: "Instagram token lacks required permissions. Ensure instagram_content_publish is enabled.",
        429: "Instagram rate limit hit. Your token is valid — try again tomorrow.",
        "timeout": "Instagram API timed out. Try again in a moment.",
    },
}


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.post("/validate-key")
def validate_key(body: dict, _: str = Depends(verify_api_key)):
    """
    Validate an external API key by making a lightweight test call.
    body: {service: 'printify'|'shopify'|'anthropic'|..., key: '...'}
    """
    service = body.get("service", "").lower()
    key = body.get("key", "")

    validators = {
        "anthropic": _validate_anthropic,
        "printify": _validate_printify,
        "shopify": _validate_shopify,
        "openai": _validate_openai,
        "klaviyo": _validate_klaviyo,
        "instagram": _validate_instagram,
    }
    validator = validators.get(service)
    if not validator:
        return _envelope({"service": service, "valid": False, "error": f"Unknown service: {service}"})

    result = validator(key)
    # Enrich error message with service-specific guidance
    if not result.get("valid") and result.get("error") and service in _SERVICE_ERROR_MESSAGES:
        raw_error = result["error"]
        messages = _SERVICE_ERROR_MESSAGES[service]
        for code, msg in messages.items():
            if str(code) in raw_error or (code == "timeout" and "timeout" in raw_error.lower()):
                result["error"] = msg
                break
    return _envelope(result)


@router.get("/status")
def onboarding_status(_: str = Depends(verify_api_key)):
    """Return which services are configured and which are missing."""
    status = {
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "openai": bool(settings.OPENAI_API_KEY),
        "replicate": bool(settings.REPLICATE_API_KEY),
        "printify": bool(settings.PRINTIFY_API_KEY and settings.PRINTIFY_SHOP_ID),
        "shopify": bool(settings.SHOPIFY_STORE_URL and settings.SHOPIFY_ACCESS_TOKEN),
        "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        "klaviyo": bool(settings.KLAVIYO_API_KEY),
        "expo": bool(settings.EXPO_ACCESS_TOKEN),
    }
    all_connected = all(status.values())
    return _envelope({"connected": status, "all_connected": all_connected})


@router.post("/complete")
def complete_onboarding(_: str = Depends(verify_api_key)):
    return _envelope({"message": "Onboarding marked complete", "ready": True})


def _validate_anthropic(key: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        client.models.list()
        return {"service": "anthropic", "valid": True}
    except Exception as e:
        return {"service": "anthropic", "valid": False, "error": str(e)}


def _validate_printify(key: str) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://api.printify.com/v1/shops.json",
                headers={"Authorization": f"Bearer {key}"},
            )
            r.raise_for_status()
        return {"service": "printify", "valid": True}
    except Exception as e:
        return {"service": "printify", "valid": False, "error": str(e)}


def _validate_shopify(key: str) -> dict:
    store_url = settings.SHOPIFY_STORE_URL
    if not store_url:
        return {"service": "shopify", "valid": False, "error": "SHOPIFY_STORE_URL not set"}
    try:
        base = store_url.rstrip("/")
        if not base.startswith("https://"):
            base = f"https://{base}"
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"{base}/admin/api/2024-01/shop.json",
                headers={"X-Shopify-Access-Token": key},
            )
            r.raise_for_status()
        return {"service": "shopify", "valid": True}
    except Exception as e:
        return {"service": "shopify", "valid": False, "error": str(e)}


def _validate_openai(key: str) -> dict:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        client.models.list()
        return {"service": "openai", "valid": True}
    except Exception as e:
        return {"service": "openai", "valid": False, "error": str(e)}


def _validate_klaviyo(key: str) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://a.klaviyo.com/api/accounts/",
                headers={
                    "Authorization": f"Klaviyo-API-Key {key}",
                    "revision": "2024-02-15",
                },
            )
            r.raise_for_status()
        return {"service": "klaviyo", "valid": True}
    except Exception as e:
        return {"service": "klaviyo", "valid": False, "error": str(e)}


def _validate_instagram(key: str) -> dict:
    account_id = settings.INSTAGRAM_ACCOUNT_ID
    if not account_id:
        return {"service": "instagram", "valid": False, "error": "INSTAGRAM_ACCOUNT_ID not set"}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"https://graph.facebook.com/v19.0/{account_id}",
                params={"fields": "id,name", "access_token": key},
            )
            r.raise_for_status()
        return {"service": "instagram", "valid": True}
    except Exception as e:
        return {"service": "instagram", "valid": False, "error": str(e)}
