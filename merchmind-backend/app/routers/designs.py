"""
Design review queue endpoints — approve, reject, delay, regenerate.
"""
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.design import Design
from app.models.trend import Trend
from app.models.feedback_log import FeedbackLog
from app.schemas.design import DesignOut, DesignQueueItem, DelayRequest, RegenerateRequest
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/designs", tags=["designs"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Return all non-deleted, non-rejected designs across all batches."""
    designs = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.collection))
        .filter(
            Design.is_deleted == False,
            Design.status.in_(["ready", "approved", "delayed"]),
        )
        .order_by(Design.created_at.desc())
        .all()
    )

    result = []
    for d in designs:
        item = DesignQueueItem.model_validate(d)
        if d.trend:
            item.claude_reasoning = d.trend.claude_reasoning
        data = item.model_dump()
        if d.collection:
            data["collection_name"] = d.collection.name
        result.append(data)
    return _envelope(result)


@router.get("/{design_id}")
def get_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    design = (
        db.query(Design)
        .options(joinedload(Design.products), joinedload(Design.marketing_assets), joinedload(Design.trend))
        .filter(Design.id == design_id, Design.is_deleted == False)
        .first()
    )
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    return _envelope(DesignOut.model_validate(design).model_dump())


@router.patch("/{design_id}/approve")
def approve_design(
    design_id: UUID,
    publish: bool = True,
    product_types: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Approve a design. Optionally publish only selected product types (comma-separated)."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.status = "approved"
    design.approved_at = datetime.utcnow()
    _log_feedback(db, design, "approved")
    db.commit()

    selected_types = set(product_types.split(",")) if product_types else None

    published = []
    skipped = []
    failed = []
    if publish:
        from app.models.product import Product
        from app.services.publishing.printify_publisher import _get as _get_printify
        svc = _get_printify()
        products = db.query(Product).filter(Product.design_id == design_id).all()
        for product in products:
            if selected_types and product.product_type not in selected_types:
                skipped.append(product.product_type)
                continue
            if product.printify_product_id:
                try:
                    svc.publish_product(product.printify_product_id)
                    product.publish_status = "live"
                    product.published_at = datetime.utcnow()
                    db.commit()
                    published.append(product.product_type)
                except Exception as e:
                    product.publish_status = "failed"
                    db.commit()
                    failed.append({"type": product.product_type, "error": str(e)})
                    logger.warning(f"Publish failed for {product.product_type}: {e}")

    return _envelope({
        "id": str(design_id),
        "status": "approved",
        "published": published,
        "skipped": skipped,
        "failed": failed,
    })


@router.patch("/{design_id}/reject")
def reject_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.status = "rejected"
    design.rejected_at = datetime.utcnow()
    design.is_deleted = True
    _log_feedback(db, design, "rejected")
    db.commit()
    return _envelope({"id": str(design_id), "status": "rejected"})


@router.patch("/{design_id}/delay")
def delay_design(
    design_id: UUID,
    body: DelayRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.status = "delayed"
    design.delayed_to_week = body.delayed_to_week
    _log_feedback(db, design, "delayed")
    db.commit()
    return _envelope({"id": str(design_id), "status": "delayed", "delayed_to_week": str(body.delayed_to_week)})


@router.post("/{design_id}/regenerate")
def regenerate_design(
    design_id: UUID,
    body: RegenerateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Trigger a design regeneration with optional new prompt/archetype override."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    _log_feedback(db, design, "regenerated", edited_prompt=body.new_prompt)
    db.commit()

    from app.tasks.batch_pipeline import _generate_design_for_trend
    from app.models.settings import AppSettings
    settings_row = db.query(AppSettings).first()
    task = _generate_design_for_trend.delay(
        str(design.trend_id),
        str(design.batch_id),
        {
            "quality_threshold": settings_row.quality_threshold if settings_row else 28,
            "trend_boost_max": float(settings_row.trend_boost_max) if settings_row else 0.20,
            "base_markup": settings_row.base_markup if settings_row else {},
            "floor_prices": settings_row.floor_prices if settings_row else {},
            "force_archetype": body.force_archetype,
            "custom_prompt": body.new_prompt,
        },
    )
    return _envelope({"task_id": task.id, "message": "Regeneration queued"})


@router.get("/{design_id}/versions")
def get_design_versions(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    versions = db.query(Design).filter(Design.parent_design_id == design_id).all()
    result = [DesignOut.model_validate(v).model_dump() for v in [design] + versions]
    return _envelope(result)


@router.get("/preferences/summary")
def get_preferences(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    from app.services.design.preference_learner import get_preference_summary
    return _envelope(get_preference_summary(db))


def _log_feedback(db, design: Design, action: str, edited_prompt: str = None):
    log = FeedbackLog(
        design_id=design.id,
        action=action,
        original_prompt=design.image_prompt or "",
        edited_prompt=edited_prompt,
        week=datetime.utcnow().date(),
    )
    db.add(log)
