"""
Trend approval gate — list scored trends, approve/reject per-trend, bulk actions.
Used by the dashboard between batch scoring and design generation.
"""
import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.batch import Batch
from app.models.trend import Trend
from app.routers.auth import verify_api_key
from app.config import settings

router = APIRouter(prefix="/trends", tags=["trends"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


def _trend_to_dict(t: Trend) -> dict:
    return {
        "id": str(t.id),
        "batch_id": str(t.batch_id),
        "source": t.source,
        "raw_signal": t.raw_signal,
        "source_url": t.source_url,
        "source_metadata": t.source_metadata or {},
        "trend_score": t.trend_score,
        "viability_score": t.viability_score,
        "final_score": t.final_score,
        "claude_reasoning": t.claude_reasoning,
        "risk_flag": t.risk_flag,
        "risk_reason": t.risk_reason,
        "status": t.status,
        "approval_status": t.approval_status,
        "selected_generator": t.selected_generator,
        "proposed_archetype": t.proposed_archetype,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/batch/{batch_id}")
def list_batch_trends(
    batch_id: UUID,
    approval_status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """List all scored trends for a batch. Optionally filter by approval_status."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")

    q = db.query(Trend).filter(
        Trend.batch_id == batch_id,
        Trend.status == "queued",
    )
    if approval_status:
        q = q.filter(Trend.approval_status == approval_status)
    trends = q.order_by(Trend.final_score.desc()).all()

    generator_costs = {
        "dalle3": settings.DALLE3_COST_PER_IMAGE,
        "ideogram": settings.IDEOGRAM_COST_PER_IMAGE,
        "flux_schnell": settings.FLUX_SCHNELL_COST_PER_IMAGE,
        "text_only": 0.0,
    }

    return _envelope({
        "trends": [_trend_to_dict(t) for t in trends],
        "batch_status": batch.status,
        "generator_costs": generator_costs,
    })


class TrendApproveBody(BaseModel):
    selected_generator: Optional[str] = None  # dalle3 | flux_schnell | ideogram | text_only


@router.patch("/{trend_id}/approve")
def approve_trend(
    trend_id: UUID,
    body: TrendApproveBody = TrendApproveBody(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, f"Trend {trend_id} not found")
    trend.approval_status = "approved"
    if body.selected_generator:
        trend.selected_generator = body.selected_generator
    db.commit()
    return _envelope(_trend_to_dict(trend))


@router.patch("/{trend_id}/reject")
def reject_trend(
    trend_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, f"Trend {trend_id} not found")
    trend.approval_status = "rejected"
    db.commit()
    return _envelope(_trend_to_dict(trend))


class BulkTrendAction(BaseModel):
    trend_ids: list[str]
    action: str  # approve | reject
    selected_generator: Optional[str] = None


@router.post("/bulk-action")
def bulk_trend_action(
    body: BulkTrendAction,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")

    updated = 0
    for tid in body.trend_ids:
        try:
            trend = db.query(Trend).filter(Trend.id == tid).first()
            if trend:
                trend.approval_status = body.action + "d" if body.action != "approve" else "approved"
                if body.action == "approve":
                    trend.approval_status = "approved"
                    if body.selected_generator:
                        trend.selected_generator = body.selected_generator
                else:
                    trend.approval_status = "rejected"
                updated += 1
        except Exception as e:
            logger.warning("bulk_action: failed for trend %s: %s", tid, e)

    db.commit()
    return _envelope({"updated": updated, "action": body.action})


@router.patch("/{trend_id}/generator")
def set_trend_generator(
    trend_id: UUID,
    body: TrendApproveBody,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Update just the selected_generator for a trend without changing approval status."""
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, f"Trend {trend_id} not found")
    if body.selected_generator:
        trend.selected_generator = body.selected_generator
    db.commit()
    return _envelope(_trend_to_dict(trend))
