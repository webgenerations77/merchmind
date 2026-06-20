"""
Check API credit balances for Claude, OpenAI, and Replicate.
Returns balance info so the dashboard can warn before starting expensive runs.
"""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)
_TIMEOUT = 10


def check_anthropic_balance() -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://api.anthropic.com/v1/messages/count_tokens",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
            )
            if r.status_code == 401:
                return {"service": "claude", "ok": False, "error": "Invalid API key"}
            if r.status_code == 429:
                return {"service": "claude", "ok": False, "error": "Rate limited — may be out of credits"}
            return {"service": "claude", "ok": True, "status": "active"}
    except Exception as e:
        return {"service": "claude", "ok": False, "error": str(e)}


def check_openai_balance() -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            )
            if r.status_code == 401:
                return {"service": "openai", "ok": False, "error": "Invalid API key"}
            if r.status_code == 429:
                return {"service": "openai", "ok": False, "error": "Rate limited — may be out of credits"}
            return {"service": "openai", "ok": True, "status": "active"}
    except Exception as e:
        return {"service": "openai", "ok": False, "error": str(e)}


def check_replicate_balance() -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://api.replicate.com/v1/account",
                headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"},
            )
            if r.status_code == 401:
                return {"service": "replicate", "ok": False, "error": "Invalid API key"}
            if r.status_code == 200:
                data = r.json()
                return {
                    "service": "replicate",
                    "ok": True,
                    "status": "active",
                    "type": data.get("type"),
                    "username": data.get("username"),
                }
            return {"service": "replicate", "ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"service": "replicate", "ok": False, "error": str(e)}


def check_all_balances() -> dict:
    results = {
        "claude": check_anthropic_balance(),
        "openai": check_openai_balance(),
        "replicate": check_replicate_balance(),
    }
    all_ok = all(r["ok"] for r in results.values())
    return {"ok": all_ok, "services": results}
