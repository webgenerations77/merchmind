"""
API usage tracking endpoints.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_usage_log import ApiUsageLog
from app.routers.auth import verify_api_key
from app.config import settings

router = APIRouter(prefix="/api-usage", tags=["api_usage"])
logger = logging.getLogger(__name__)

_balance_cache: dict = {}
_CACHE_TTL = 60


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("/summary")
def usage_summary(
    period: str = Query("month", regex="^(day|week|month|all)$"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    now = datetime.now(timezone.utc)
    if period == "day":
        cutoff = now - timedelta(days=1)
    elif period == "week":
        cutoff = now - timedelta(weeks=1)
    elif period == "month":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)

    query = db.query(ApiUsageLog).filter(ApiUsageLog.created_at >= cutoff)

    by_service = (
        query.with_entities(
            ApiUsageLog.service,
            func.count().label("calls"),
            func.sum(ApiUsageLog.input_tokens).label("input_tokens"),
            func.sum(ApiUsageLog.output_tokens).label("output_tokens"),
            func.sum(ApiUsageLog.estimated_cost).label("total_cost"),
        )
        .group_by(ApiUsageLog.service)
        .all()
    )

    by_operation = (
        query.with_entities(
            ApiUsageLog.service,
            ApiUsageLog.operation,
            ApiUsageLog.model,
            func.count().label("calls"),
            func.sum(ApiUsageLog.estimated_cost).label("total_cost"),
        )
        .group_by(ApiUsageLog.service, ApiUsageLog.operation, ApiUsageLog.model)
        .all()
    )

    daily = (
        query.with_entities(
            func.date_trunc('day', ApiUsageLog.created_at).label("day"),
            ApiUsageLog.service,
            func.sum(ApiUsageLog.estimated_cost).label("cost"),
            func.count().label("calls"),
        )
        .group_by("day", ApiUsageLog.service)
        .order_by("day")
        .all()
    )

    total_cost = sum(float(r.total_cost or 0) for r in by_service)
    total_calls = sum(int(r.calls or 0) for r in by_service)

    return _envelope({
        "period": period,
        "total_cost": round(total_cost, 4),
        "total_calls": total_calls,
        "by_service": [
            {
                "service": r.service,
                "calls": int(r.calls or 0),
                "input_tokens": int(r.input_tokens or 0),
                "output_tokens": int(r.output_tokens or 0),
                "total_cost": round(float(r.total_cost or 0), 4),
            }
            for r in by_service
        ],
        "by_operation": [
            {
                "service": r.service,
                "operation": r.operation,
                "model": r.model,
                "calls": int(r.calls or 0),
                "total_cost": round(float(r.total_cost or 0), 4),
            }
            for r in by_operation
        ],
        "daily": [
            {
                "day": r.day.isoformat() if r.day else None,
                "service": r.service,
                "cost": round(float(r.cost or 0), 4),
                "calls": int(r.calls or 0),
            }
            for r in daily
        ],
    })


@router.get("/history")
def usage_history(
    period: str = Query("day", regex="^(day|week|month|all)$"),
    service: str | None = None,
    operation: str | None = None,
    limit: int = Query(200, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Return individual API call logs, newest first."""
    now = datetime.now(timezone.utc)
    if period == "day":
        cutoff = now - timedelta(days=1)
    elif period == "week":
        cutoff = now - timedelta(weeks=1)
    elif period == "month":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)

    query = db.query(ApiUsageLog).filter(ApiUsageLog.created_at >= cutoff)
    if service:
        query = query.filter(ApiUsageLog.service == service)
    if operation:
        query = query.filter(ApiUsageLog.operation == operation)

    total = query.count()
    rows = query.order_by(desc(ApiUsageLog.created_at)).offset(offset).limit(limit).all()

    return _envelope({
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": str(r.id),
                "service": r.service,
                "operation": r.operation,
                "model": r.model,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "estimated_cost": round(float(r.estimated_cost or 0), 6),
                "design_id": str(r.design_id) if r.design_id else None,
                "batch_id": str(r.batch_id) if r.batch_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    })


def _fetch_openai_balance() -> dict:
    """Check OpenAI billing — no public balance API exists."""
    return {
        "service": "openai",
        "available": False,
        "message": "OpenAI does not expose a balance API",
        "console_url": "https://platform.openai.com/usage",
    }


def _fetch_anthropic_balance() -> dict:
    """Check Anthropic billing — no public balance API exists."""
    return {
        "service": "anthropic",
        "available": False,
        "message": "Anthropic does not expose a balance API",
        "console_url": "https://console.anthropic.com/settings/billing",
    }


def _fetch_replicate_balance() -> dict:
    """Fetch Replicate account balance via their API."""
    import httpx
    key = settings.REPLICATE_API_KEY
    if not key:
        return {"service": "replicate", "available": False, "message": "No API key configured", "console_url": "https://replicate.com/account/billing"}
    try:
        resp = httpx.get(
            "https://api.replicate.com/v1/account",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "service": "replicate",
                "available": True,
                "username": data.get("username"),
                "type": data.get("type"),
                "console_url": "https://replicate.com/account/billing",
            }
    except Exception as e:
        logger.warning("Replicate balance check failed: %s", e)
    return {"service": "replicate", "available": False, "message": "Could not reach Replicate API", "console_url": "https://replicate.com/account/billing"}


def _fetch_printify_balance() -> dict:
    """Check Printify account — no balance API, but verify connection."""
    import httpx
    key = settings.PRINTIFY_API_KEY
    if not key:
        return {"service": "printify", "available": False, "message": "No API key configured", "console_url": "https://printify.com/app/account/billing"}
    try:
        resp = httpx.get(
            "https://api.printify.com/v1/shops.json",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            shops = resp.json()
            return {
                "service": "printify",
                "available": True,
                "shop_count": len(shops),
                "message": "Connected",
                "console_url": "https://printify.com/app/account/billing",
            }
    except Exception as e:
        logger.warning("Printify check failed: %s", e)
    return {"service": "printify", "available": False, "message": "Could not reach Printify API", "console_url": "https://printify.com/app/account/billing"}


@router.get("/balances")
def api_balances(_: str = Depends(verify_api_key)):
    """Return current balance/status for each API provider. Cached for 60s."""
    global _balance_cache
    now = time.time()
    if _balance_cache and now - _balance_cache.get("_ts", 0) < _CACHE_TTL:
        return _envelope(_balance_cache["data"])

    providers = [
        _fetch_anthropic_balance(),
        _fetch_openai_balance(),
        _fetch_replicate_balance(),
        _fetch_printify_balance(),
    ]

    result = {
        "providers": providers,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    _balance_cache = {"data": result, "_ts": now}
    return _envelope(result)
