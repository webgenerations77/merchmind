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
def get_review_queue(
    filter: str = "active",
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Return designs for review. filter=active (default), filter=archived, filter=all."""
    if filter == "archived":
        statuses = ["archived"]
    elif filter == "all":
        statuses = ["ready", "approved", "delayed", "archived"]
    else:
        statuses = ["ready", "approved", "delayed"]

    designs = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.collection))
        .filter(
            Design.is_deleted == False,
            Design.status.in_(statuses),
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
        if d.collection_id:
            data["source"] = "collection"
        elif d.trend_id:
            data["source"] = "batch"
        else:
            data["source"] = "drews_mind"
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
    removed = []
    failed = []
    if publish:
        from app.models.product import Product
        from app.services.publishing.printify_publisher import _get as _get_printify
        svc = _get_printify()
        products = db.query(Product).filter(Product.design_id == design_id).all()
        for product in products:
            if selected_types and product.product_type not in selected_types:
                if product.printify_product_id:
                    try:
                        svc.delete_product(product.printify_product_id)
                    except Exception as e:
                        logger.warning(f"Printify delete failed for deselected {product.product_type}: {e}")
                db.delete(product)
                removed.append(product.product_type)
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
        db.commit()

    return _envelope({
        "id": str(design_id),
        "status": "approved",
        "published": published,
        "removed": removed,
        "failed": failed,
    })


@router.patch("/{design_id}/reject")
def reject_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Permanently delete a design — removes Supabase assets, Printify drafts, and DB records."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    _log_feedback(db, design, "rejected")
    did = str(design.id)

    # Delete Printify drafts
    deleted_printify = []
    from app.models.product import Product
    from app.services.publishing.printify_publisher import _get as _get_printify
    svc = _get_printify()
    products = db.query(Product).filter(Product.design_id == design_id).all()
    for product in products:
        if product.printify_product_id:
            try:
                svc.delete_product(product.printify_product_id)
                deleted_printify.append(product.product_type)
            except Exception as e:
                logger.warning(f"Printify delete failed for {product.product_type}: {e}")

    # Delete Supabase storage assets
    from app.utils.storage import storage
    deleted_assets = []
    for path in [
        storage.design_raw_path(did),
        storage.design_processed_path(did),
        storage.design_light_variant_path(did),
    ]:
        try:
            storage.delete(path)
            deleted_assets.append(path)
        except Exception:
            pass
    for pt in ["tshirt", "mug", "hat", "phone_case", "sticker", "poster"]:
        for variant in ["front", "back", "lifestyle"]:
            try:
                storage.delete(storage.mockup_path(did, pt, variant))
                deleted_assets.append(f"mockups/{pt}/{variant}")
            except Exception:
                pass

    # Delete DB records (cascade: marketing_assets, feedback_logs, alerts, products, then design)
    from app.models.marketing_asset import MarketingAsset
    from app.models.alert import Alert
    db.query(MarketingAsset).filter(MarketingAsset.design_id == design_id).delete(synchronize_session=False)
    db.query(FeedbackLog).filter(FeedbackLog.design_id == design_id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.design_id == design_id).delete(synchronize_session=False)
    db.query(Product).filter(Product.design_id == design_id).delete(synchronize_session=False)
    db.query(Design).filter(Design.parent_design_id == design_id).update(
        {Design.parent_design_id: None}, synchronize_session=False
    )
    db.delete(design)
    db.commit()

    logger.info("Design %s permanently deleted: %d printify, %d assets", did, len(deleted_printify), len(deleted_assets))
    return _envelope({"id": did, "status": "deleted", "printify_deleted": deleted_printify, "assets_deleted": len(deleted_assets)})


@router.patch("/{design_id}/archive")
def archive_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Archive a design — removes from active queue, recoverable."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.status = "archived"
    design.archived_at = datetime.utcnow()
    _log_feedback(db, design, "archived")
    db.commit()
    return _envelope({"id": str(design_id), "status": "archived"})


@router.patch("/{design_id}/unarchive")
def unarchive_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Restore an archived design to the review queue."""
    design = db.query(Design).filter(Design.id == design_id, Design.status == "archived").first()
    if not design:
        raise HTTPException(404, f"Archived design {design_id} not found")
    design.status = "ready"
    design.archived_at = None
    _log_feedback(db, design, "unarchived")
    db.commit()
    return _envelope({"id": str(design_id), "status": "ready"})


@router.patch("/{design_id}/revisit")
def revisit_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Move a design to the bottom of the review queue with a revisit badge."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.revisit_count = (design.revisit_count or 0) + 1
    design.created_at = datetime.utcnow()
    design.status = "ready"
    _log_feedback(db, design, "revisited")
    db.commit()
    return _envelope({"id": str(design_id), "status": "ready", "revisit_count": design.revisit_count})


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
