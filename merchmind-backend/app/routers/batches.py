"""
Batch management endpoints including SSE progress streaming.
"""
import csv
import io
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
import redis as redis_lib

from app.database import get_db
from app.models.batch import Batch
from app.models.batch_item import BatchItem
from app.models.design import Design
from app.models.product import Product
from app.models.trend import Trend
from app.schemas.batch import BatchOut, BatchItemOut, BatchDetailOut
from app.routers.auth import verify_api_key
from app.config import settings

router = APIRouter(prefix="/batches", tags=["batches"])
logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


def _delete_printify_products(db: Session, design_ids: list) -> int:
    """Delete the Printify draft products for these designs before their DB rows
    are removed, so a purge doesn't orphan drafts in the Printify shop. Best
    effort — a failed delete is logged and skipped, never blocks the purge.
    """
    if not design_ids:
        return 0
    from app.services.publishing.printify_publisher import delete_product as printify_delete
    deleted = 0
    products = db.query(Product).filter(
        Product.design_id.in_(design_ids), Product.printify_product_id.isnot(None)
    ).all()
    for p in products:
        try:
            printify_delete(p.printify_product_id)
            deleted += 1
        except Exception as e:
            logger.warning("purge: Printify delete failed for %s: %s", p.printify_product_id, e)
    return deleted


@router.get("")
def list_batches(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batches = db.query(Batch).order_by(Batch.created_at.desc()).limit(50).all()
    return _envelope([BatchOut.model_validate(b).model_dump() for b in batches])


@router.get("/current")
def get_current_batch(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batch = db.query(Batch).order_by(Batch.created_at.desc()).first()
    if not batch:
        return _envelope(None)
    return _envelope(BatchOut.model_validate(batch).model_dump())


@router.get("/{batch_id}")
def get_batch(batch_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    return _envelope(BatchOut.model_validate(batch).model_dump())


@router.post("/trigger")
def trigger_batch(
    body: Optional[dict] = None,
    max_designs: Optional[int] = None,
    max_trends: Optional[int] = None,
    _: str = Depends(verify_api_key),
):
    """Manually trigger the weekly batch pipeline with optional configuration."""
    from app.tasks.batch_pipeline import run_weekly_batch

    config = body or {}
    num_designs = config.get("num_designs") or max_designs
    trend_sources = config.get("trend_sources")
    style_filter = config.get("style_filter")
    product_focus = config.get("product_focus")
    pause_after_scoring = config.get("pause_after_scoring", False)

    task = run_weekly_batch.delay(
        None,
        num_designs,
        max_trends,
        trend_sources=trend_sources,
        style_filter=style_filter,
        product_focus=product_focus,
        pause_after_scoring=pause_after_scoring,
    )
    return _envelope({
        "task_id": task.id,
        "message": "Batch pipeline triggered",
        "max_designs": num_designs,
        "max_trends": max_trends,
        "trend_sources": trend_sources,
        "style_filter": style_filter,
        "product_focus": product_focus,
        "pause_after_scoring": pause_after_scoring,
    })


@router.post("/{batch_id}/generate-approved")
def generate_approved(
    batch_id: UUID,
    body: Optional[dict] = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Start design generation for approved trends.
    Called after the user has approved/rejected trends in the approval gate.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    if batch.status not in ("pending_approval", "running"):
        raise HTTPException(409, f"Batch {batch_id} is in status '{batch.status}', cannot generate")

    # Flip to "running" synchronously, before dispatching the async task. The
    # Celery task also sets this, but worker-pickup latency leaves a window
    # where the batch still reads "pending_approval" — during which the
    # dashboard's status poll reverts the UI back to the approval gate, making
    # it look like generation never started.
    batch.status = "running"
    db.commit()

    config = body or {}
    from app.tasks.batch_pipeline import generate_approved_designs
    task = generate_approved_designs.delay(
        str(batch_id),
        style_filter=config.get("style_filter"),
        product_focus=config.get("product_focus"),
    )
    return _envelope({"task_id": task.id, "message": "Generation started for approved trends"})


@router.post("/{batch_id}/cancel")
def cancel_batch(
    batch_id: UUID,
    purge: bool = False,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Cancel a stuck batch. With purge=true, also deletes its designs/products/trends."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")

    batch.status = "failed"
    batch.run_completed_at = datetime.utcnow()

    stuck = db.query(Design).filter(
        Design.batch_id == batch_id, Design.status == "generating"
    ).all()
    for d in stuck:
        d.status = "rejected"
        d.rejected_at = datetime.utcnow()

    purged = {}
    if purge:
        from app.models.marketing_asset import MarketingAsset
        from app.models.feedback_log import FeedbackLog
        from app.models.alert import Alert
        from app.models.trend import Trend

        designs = db.query(Design).filter(Design.batch_id == batch_id).all()
        design_ids = [d.id for d in designs]
        printify_deleted = 0
        if design_ids:
            printify_deleted = _delete_printify_products(db, design_ids)
            db.query(MarketingAsset).filter(MarketingAsset.design_id.in_(design_ids)).delete(synchronize_session=False)
            db.query(FeedbackLog).filter(FeedbackLog.design_id.in_(design_ids)).delete(synchronize_session=False)
            db.query(Alert).filter(Alert.design_id.in_(design_ids)).delete(synchronize_session=False)
            db.query(Product).filter(Product.design_id.in_(design_ids)).delete(synchronize_session=False)
            # Clear self-referencing parent_design_id before deleting
            db.query(Design).filter(Design.parent_design_id.in_(design_ids)).update(
                {Design.parent_design_id: None}, synchronize_session=False
            )
        db.query(Alert).filter(Alert.batch_id == batch_id).delete(synchronize_session=False)
        item_count = db.query(BatchItem).filter(BatchItem.batch_id == batch_id).delete(synchronize_session=False)
        prod_count = len(design_ids)
        design_count = db.query(Design).filter(Design.batch_id == batch_id).delete(synchronize_session=False)
        trend_count = db.query(Trend).filter(Trend.batch_id == batch_id).delete(synchronize_session=False)
        purged = {"designs_deleted": design_count, "products_deleted": prod_count, "printify_products_deleted": printify_deleted, "trends_deleted": trend_count, "items_deleted": item_count}

    try:
        _redis.flushdb()
        purged["redis_flushed"] = True
    except Exception:
        purged["redis_flushed"] = False

    db.commit()
    logger.info("Batch %s cancelled (purge=%s) %s", batch_id, purge, purged)
    return _envelope({"batch_id": str(batch_id), "status": "failed", "stuck_designs_rejected": len(stuck), **purged})


@router.delete("/{batch_id}")
def delete_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Permanently delete a terminal (failed/complete) batch and all its children.
    Refuses to delete a running or pending_approval batch — cancel it first."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    if batch.status in ("running", "pending_approval"):
        raise HTTPException(409, f"Batch {batch_id} is '{batch.status}'; cancel it before deleting")

    from app.models.marketing_asset import MarketingAsset
    from app.models.feedback_log import FeedbackLog
    from app.models.alert import Alert

    designs = db.query(Design).filter(Design.batch_id == batch_id).all()
    design_ids = [d.id for d in designs]
    printify_deleted = 0
    if design_ids:
        printify_deleted = _delete_printify_products(db, design_ids)
        db.query(MarketingAsset).filter(MarketingAsset.design_id.in_(design_ids)).delete(synchronize_session=False)
        db.query(FeedbackLog).filter(FeedbackLog.design_id.in_(design_ids)).delete(synchronize_session=False)
        db.query(Alert).filter(Alert.design_id.in_(design_ids)).delete(synchronize_session=False)
        db.query(Product).filter(Product.design_id.in_(design_ids)).delete(synchronize_session=False)
        db.query(Design).filter(Design.parent_design_id.in_(design_ids)).update(
            {Design.parent_design_id: None}, synchronize_session=False
        )
    db.query(Alert).filter(Alert.batch_id == batch_id).delete(synchronize_session=False)
    items_deleted = db.query(BatchItem).filter(BatchItem.batch_id == batch_id).delete(synchronize_session=False)
    designs_deleted = db.query(Design).filter(Design.batch_id == batch_id).delete(synchronize_session=False)
    trends_deleted = db.query(Trend).filter(Trend.batch_id == batch_id).delete(synchronize_session=False)
    db.delete(batch)
    db.commit()

    logger.info("Batch %s deleted (designs=%s trends=%s items=%s printify=%s)", batch_id, designs_deleted, trends_deleted, items_deleted, printify_deleted)
    return _envelope({
        "batch_id": str(batch_id),
        "deleted": True,
        "designs_deleted": designs_deleted,
        "products_deleted": len(design_ids),
        "printify_products_deleted": printify_deleted,
        "trends_deleted": trends_deleted,
        "items_deleted": items_deleted,
    })


@router.get("/{batch_id}/detail")
def get_batch_detail(batch_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Full batch detail with per-item results."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")

    items = db.query(BatchItem).filter(BatchItem.batch_id == batch_id).order_by(BatchItem.created_at).all()

    item_dicts = []
    for item in items:
        d = BatchItemOut.model_validate(item).model_dump()
        if item.design_id:
            design = db.query(Design).filter(Design.id == item.design_id).first()
            if design:
                d["processed_image_url"] = design.processed_image_url
        item_dicts.append(d)

    success_count = sum(1 for i in items if i.status == "success")
    failed_count = sum(1 for i in items if i.status == "failed")

    return _envelope({
        "batch": BatchOut.model_validate(batch).model_dump(),
        "items": item_dicts,
        "success_count": success_count,
        "failed_count": failed_count,
    })


@router.post("/{batch_id}/retry-failed")
def retry_failed_items(batch_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Re-queue failed items from a batch for regeneration."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")

    failed_items = db.query(BatchItem).filter(
        BatchItem.batch_id == batch_id, BatchItem.status == "failed"
    ).all()

    if not failed_items:
        return _envelope({"retried": 0, "message": "No failed items to retry"})

    from app.models.settings import AppSettings
    settings_row = db.query(AppSettings).first()
    quality_threshold = settings_row.quality_threshold if settings_row else 28
    trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20
    base_markup = settings_row.base_markup if settings_row else {}
    floor_prices = settings_row.floor_prices if settings_row else {}
    back_logo_url = settings_row.back_logo_url if settings_row else None
    back_logo_products = settings_row.back_logo_products if settings_row else ["tshirt", "hat"]
    marketing_enabled = settings_row.marketing_generation_enabled if settings_row else False

    from app.tasks.batch_pipeline import _generate_design_for_trend
    retried = 0
    for item in failed_items:
        if not item.trend_id:
            continue
        trend = db.query(Trend).filter(Trend.id == item.trend_id).first()
        if not trend:
            continue

        # Clean up old failed design if any
        if item.design_id:
            old_design = db.query(Design).filter(Design.id == item.design_id).first()
            if old_design and old_design.status == "rejected":
                db.query(Product).filter(Product.design_id == old_design.id).delete(synchronize_session=False)
                db.delete(old_design)

        # Create new batch item for the retry
        new_item = BatchItem(
            batch_id=batch_id,
            trend_id=item.trend_id,
            concept_name=item.concept_name,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        try:
            _generate_design_for_trend(
                str(item.trend_id), str(batch_id), {
                    "quality_threshold": quality_threshold,
                    "trend_boost_max": trend_boost_max,
                    "base_markup": base_markup,
                    "floor_prices": floor_prices,
                    "back_logo_enabled": True,
                    "back_logo_url": back_logo_url,
                    "back_logo_products": back_logo_products,
                    "archetype_bias": "image_only",
                    "marketing_generation_enabled": marketing_enabled,
                    "_batch_item_id": str(new_item.id),
                },
            )
            design = db.query(Design).filter(
                Design.batch_id == batch_id, Design.trend_id == item.trend_id
            ).order_by(Design.created_at.desc()).first()
            if design:
                new_item.design_id = design.id
                products = db.query(Product).filter(Product.design_id == design.id).all()
                new_item.product_types = [p.product_type for p in products]
            new_item.status = "success"
            new_item.completed_at = datetime.utcnow()
            batch.approved_count = (batch.approved_count or 0) + 1
            db.commit()
            retried += 1
        except Exception as e:
            import traceback
            new_item.status = "failed"
            from app.tasks.batch_pipeline import _detect_failed_step, _summarize_error
            new_item.failed_step = _detect_failed_step(e)
            new_item.error_summary = _summarize_error(e, new_item.failed_step)
            new_item.error_detail = traceback.format_exc()
            new_item.completed_at = datetime.utcnow()
            db.commit()
            logger.error("Retry failed for trend %s: %s", item.trend_id, e)

    return _envelope({"retried": retried, "total_failed": len(failed_items), "message": f"Retried {retried}/{len(failed_items)} failed items"})


@router.get("/{batch_id}/export")
def export_batch_log(batch_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Export batch results as CSV."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")

    items = db.query(BatchItem).filter(BatchItem.batch_id == batch_id).order_by(BatchItem.created_at).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Concept", "Status", "Failed Step", "Error", "Product Types", "Started", "Completed", "Duration (s)"])

    for item in items:
        duration = ""
        if item.started_at and item.completed_at:
            duration = str(round((item.completed_at - item.started_at).total_seconds(), 1))
        writer.writerow([
            item.concept_name,
            item.status,
            item.failed_step or "",
            item.error_summary or "",
            ", ".join(item.product_types or []),
            item.started_at.isoformat() if item.started_at else "",
            item.completed_at.isoformat() if item.completed_at else "",
            duration,
        ])

    # If no batch items exist, fall back to designs linked to the batch
    if not items:
        designs = db.query(Design).filter(Design.batch_id == batch_id).all()
        for d in designs:
            products = db.query(Product).filter(Product.design_id == d.id).all()
            writer.writerow([
                d.concept_name,
                "success" if d.status == "ready" else "failed",
                "" if d.status == "ready" else "design_generation",
                "" if d.status == "ready" else f"Status: {d.status}",
                ", ".join(p.product_type for p in products),
                d.created_at.isoformat() if d.created_at else "",
                "",
                "",
            ])

    csv_content = output.getvalue()
    filename = f"batch_{str(batch_id)[:8]}_{batch.week_start}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{batch_id}/progress")
async def stream_batch_progress(batch_id: UUID, _: str = Depends(verify_api_key)):
    """
    SSE endpoint: streams batch progress events in real-time.
    Clients receive JSON events as the pipeline advances through steps.
    """
    channel = f"batch_progress:{batch_id}"

    async def event_generator():
        pubsub = _redis.pubsub()
        pubsub.subscribe(channel)
        try:
            # First send current batch state
            yield f"data: {json.dumps({'type': 'connected', 'batch_id': str(batch_id)})}\n\n"
            # Stream events for up to 2 hours
            timeout = 7200
            elapsed = 0
            while elapsed < timeout:
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                await asyncio.sleep(0.1)
                elapsed += 1
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
