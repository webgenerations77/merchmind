"""
API usage tracking endpoints.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_usage_log import ApiUsageLog
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/api-usage", tags=["api_usage"])


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
