"""
Design review queue endpoints — approve, reject, delay, regenerate.
"""
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from sqlalchemy import func as sa_func
from app.database import get_db
from app.models.design import Design
from app.models.trend import Trend
from app.models.feedback_log import FeedbackLog
from app.models.api_usage_log import ApiUsageLog
from app.schemas.design import DesignOut, DesignQueueItem, DelayRequest, RegenerateRequest, ChatMessageIn, SuggestRegenerateRequest
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
        statuses = ["ready", "delayed", "approved", "archived"]
    else:
        statuses = ["ready", "delayed"]

    designs = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.collection), joinedload(Design.products))
        .filter(
            Design.is_deleted == False,
            Design.status.in_(statuses),
        )
        .order_by(Design.created_at.desc())
        .all()
    )

    design_ids = [d.id for d in designs]
    cost_rows = (
        db.query(ApiUsageLog.design_id, sa_func.sum(ApiUsageLog.estimated_cost))
        .filter(ApiUsageLog.design_id.in_(design_ids))
        .group_by(ApiUsageLog.design_id)
        .all()
    ) if design_ids else []
    cost_map = {str(row[0]): float(row[1]) for row in cost_rows}

    result = []
    for d in designs:
        item = DesignQueueItem.model_validate(d)
        if d.trend:
            item.claude_reasoning = d.trend.claude_reasoning
        data = item.model_dump()
        if d.collection:
            data["collection_name"] = d.collection.name
        primary_pt = d.primary_product_type
        if not primary_pt:
            primary_pt = d.products[0].product_type if d.products else "tshirt"
            logger.warning("Design %s missing primary_product_type, defaulting to %s", d.id, primary_pt)
        primary_product = next((p for p in d.products if p.product_type == primary_pt and p.mockup_urls), None)
        if primary_product and primary_product.mockup_urls.get("front"):
            data["primary_mockup_url"] = primary_product.mockup_urls["front"]
        data["product_count"] = len(d.products)
        data["ai_cost"] = round(cost_map.get(str(d.id), 0), 4)
        if d.collection_id:
            data["source"] = "collection"
        elif d.trend_id:
            data["source"] = "batch"
        else:
            data["source"] = "drews_mind"
        result.append(data)
    return _envelope(result)


@router.get("/featured")
def get_featured_designs(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Return all featured designs (any status except deleted), newest-featured first."""
    designs = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.products))
        .filter(Design.is_featured == True, Design.is_deleted == False)
        .order_by(Design.featured_at.desc().nullslast(), Design.created_at.desc())
        .all()
    )
    result = []
    for d in designs:
        item = DesignQueueItem.model_validate(d)
        if d.trend:
            item.claude_reasoning = d.trend.claude_reasoning
        data = item.model_dump()
        primary_pt = d.primary_product_type or "tshirt"
        primary_product = next((p for p in d.products if p.product_type == primary_pt and p.mockup_urls), None)
        if primary_product and primary_product.mockup_urls.get("front"):
            data["primary_mockup_url"] = primary_product.mockup_urls["front"]
        data["product_count"] = len(d.products)
        data["featured_at"] = d.featured_at.isoformat() if d.featured_at else None
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
    data = DesignOut.model_validate(design).model_dump()
    if design.trend:
        data["trend_source"] = design.trend.source
        data["trend_signal"] = design.trend.raw_signal
        data["trend_source_metadata"] = design.trend.source_metadata or {}
        data["trend_score"] = design.trend.trend_score
        data["viability_score"] = design.trend.viability_score
        data["final_score"] = design.trend.final_score
        data["claude_reasoning"] = design.trend.claude_reasoning
    return _envelope(data)


@router.patch("/{design_id}/approve")
def approve_design(
    design_id: UUID,
    publish: bool = True,
    product_types: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Approve and publish a design.

    Design state machine (approve path):
      ready/delayed → approved   (at least one product published, or publish=false)
      ready/delayed → ready      (ALL products failed — stays in queue for retry)
      approved      → 409        (already approved — rejected to prevent double-publish)

    Product publish_status transitions: pending → live | failed.
    """
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    if design.status == "approved":
        raise HTTPException(409, f"Design {design_id} is already approved")

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
                    published.append(product.product_type)
                except Exception as e:
                    product.publish_status = "failed"
                    failed.append({"type": product.product_type, "error": str(e)})
                    logger.warning(f"Publish failed for {product.product_type}: {e}")

    if not publish or len(published) > 0 or len(failed) == 0:
        design.status = "approved"
        design.approved_at = datetime.utcnow()
        _log_feedback(db, design, "approved")
    else:
        _log_feedback(db, design, "publish_failed")

    db.commit()

    final_status = design.status
    return _envelope({
        "id": str(design_id),
        "status": final_status,
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

    try:
        return _perform_reject(design, design_id, db)
    except Exception as e:
        db.rollback()
        logger.exception("Reject failed for design %s", design_id)
        raise HTTPException(500, f"Reject failed: {type(e).__name__}: {e}")


def _perform_reject(design: Design, design_id: UUID, db: Session):
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
    for pt in ["tshirt", "mug", "hat", "phone_case", "sticker"]:
        for variant in ["front", "back", "lifestyle"]:
            try:
                storage.delete(storage.mockup_path(did, pt, variant))
                deleted_assets.append(f"mockups/{pt}/{variant}")
            except Exception:
                pass

    # Delete DB records (cascade: batch_items, marketing_assets, feedback_logs, alerts, products, then design)
    from app.models.marketing_asset import MarketingAsset
    from app.models.alert import Alert
    from app.models.batch_item import BatchItem
    db.query(BatchItem).filter(BatchItem.design_id == design_id).update(
        {BatchItem.design_id: None}, synchronize_session=False
    )
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


@router.patch("/{design_id}/feature")
def toggle_featured(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Toggle the is_featured flag on a design."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.is_featured = not design.is_featured
    design.featured_at = datetime.utcnow() if design.is_featured else None
    db.commit()
    return _envelope({"id": str(design_id), "is_featured": design.is_featured, "featured_at": design.featured_at.isoformat() if design.featured_at else None})


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


@router.post("/{design_id}/retire")
def retire_design(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Retire all products for a design — unpublish from Printify/Shopify, mark as retired."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    from app.models.product import Product
    from app.services.publishing.printify_publisher import _get as _get_printify
    svc = _get_printify()
    products = db.query(Product).filter(Product.design_id == design_id).all()

    retired = []
    failed = []
    for product in products:
        if product.publish_status == "retired":
            continue
        if product.printify_product_id:
            try:
                svc.unpublish_product(product.printify_product_id)
            except Exception as e:
                logger.warning("Printify unpublish failed for %s: %s", product.product_type, e)
                failed.append({"type": product.product_type, "error": str(e)})
                continue
        product.publish_status = "retired"
        product.unpublished_at = datetime.utcnow()
        retired.append(product.product_type)

    _log_feedback(db, design, "retired")
    db.commit()

    logger.info("Design %s retired: %d products, %d failed", design_id, len(retired), len(failed))
    return _envelope({
        "id": str(design_id),
        "retired": retired,
        "failed": failed,
    })


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

    if not design.trend_id:
        raise HTTPException(400, "Cannot regenerate a design without a linked trend")

    _log_feedback(db, design, "regenerated", edited_prompt=body.new_prompt)
    db.commit()

    from app.tasks.batch_pipeline import _generate_design_for_trend
    from app.models.settings import AppSettings
    settings_row = db.query(AppSettings).first()
    task = _generate_design_for_trend.delay(
        str(design.trend_id),
        str(design.batch_id) if design.batch_id else str(design.trend_id),
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


@router.post("/{design_id}/chat")
def chat_with_concept(
    design_id: UUID,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Send a message to Claude about this concept. Persists conversation on the design."""
    design = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.products))
        .filter(Design.id == design_id, Design.is_deleted == False)
        .first()
    )
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    history = list(design.conversation_history or [])

    if not history:
        system_context = _build_chat_context(design)
        opening = _generate_opening_message(design)
        history.append({"role": "assistant", "content": opening})

    history.append({"role": "user", "content": body.message})

    from app.utils.claude_client import claude
    api_messages = [{"role": m["role"], "content": m["content"]} for m in history]
    system_prompt = _build_chat_context(design)

    text, _ = claude.sonnet(
        "suggest_chat",
        api_messages,
        system=system_prompt,
        max_tokens=1024,
    )

    history.append({"role": "assistant", "content": text})
    design.conversation_history = history
    db.commit()

    return _envelope({"reply": text, "conversation": history})


@router.post("/{design_id}/suggest-regenerate")
def suggest_regenerate(
    design_id: UUID,
    body: SuggestRegenerateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Synthesize conversation into a directive and regenerate the design."""
    design = (
        db.query(Design)
        .options(joinedload(Design.trend), joinedload(Design.products))
        .filter(Design.id == design_id, Design.is_deleted == False)
        .first()
    )
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    if not design.trend_id:
        raise HTTPException(400, "Cannot regenerate a design without a linked trend")

    from app.utils.claude_client import claude

    synth_messages = [{"role": m["role"], "content": m["content"]} for m in body.conversation]
    synth_messages.append({
        "role": "user",
        "content": (
            "Based on our conversation, write a concise design directive that captures "
            "all the changes I requested. This will be fed directly to the image generation "
            "pipeline. Include: desired concept changes, style/mood adjustments, text changes, "
            "and any archetype preference. Reply with ONLY the directive, no preamble."
        ),
    })

    try:
        directive, _ = claude.sonnet(
            "suggest_synthesize",
            synth_messages,
            system=_build_chat_context(design),
            max_tokens=512,
        )
    except Exception as e:
        logger.error("suggest-regenerate: Claude synthesis failed for %s: %s", design_id, e)
        raise HTTPException(502, f"Failed to synthesize design directive: {e}")

    design.conversation_history = body.conversation
    new_version = (design.version or 1) + 1
    design.version = new_version
    _log_feedback(db, design, "suggest_regenerated", edited_prompt=directive)
    db.commit()

    from app.tasks.batch_pipeline import _generate_design_for_trend
    from app.models.settings import AppSettings
    settings_row = db.query(AppSettings).first()

    try:
        task = _generate_design_for_trend.delay(
            str(design.trend_id),
            str(design.batch_id) if design.batch_id else str(design.trend_id),
            {
                "quality_threshold": settings_row.quality_threshold if settings_row else 28,
                "trend_boost_max": float(settings_row.trend_boost_max) if settings_row else 0.20,
                "base_markup": settings_row.base_markup if settings_row else {},
                "floor_prices": settings_row.floor_prices if settings_row else {},
                "custom_prompt": directive,
            },
        )
    except Exception as e:
        logger.error("suggest-regenerate: task dispatch failed for %s: %s", design_id, e)
        raise HTTPException(502, f"Failed to queue regeneration task: {e}")

    return _envelope({
        "task_id": task.id,
        "directive": directive,
        "version": new_version,
    })


@router.delete("/{design_id}/chat")
def clear_chat(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Clear the conversation history for a design."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    design.conversation_history = None
    db.commit()
    return _envelope({"id": str(design_id), "cleared": True})


def _build_chat_context(design: Design) -> str:
    """Build the system prompt with full concept context for the chat."""
    parts = [
        "You are a creative director at a print-on-demand merch company called Wear it Forward.",
        "You're discussing a design concept with Drew, the founder, who wants to iterate on it before approving.",
        "Be conversational, concise, and creative. Suggest specific improvements when asked.",
        "You have full context on this concept:",
        "",
        f"Concept: {design.concept_name}",
        f"Archetype: {design.archetype}",
        f"Quality Score: {design.quality_score}/40",
    ]
    if design.quality_breakdown:
        scores = ", ".join(f"{k}: {v}/10" for k, v in design.quality_breakdown.items())
        parts.append(f"Quality Breakdown: {scores}")
    if design.primary_text:
        parts.append(f"Primary Text: \"{design.primary_text}\"")
    if design.secondary_text:
        parts.append(f"Secondary Text: \"{design.secondary_text}\"")
    if design.tagline:
        parts.append(f"Tagline: \"{design.tagline}\"")
    if design.image_prompt:
        parts.append(f"Image Prompt Used: {design.image_prompt}")
    if design.shopify_title:
        parts.append(f"Shopify Title: {design.shopify_title}")
    if design.font_pair:
        parts.append(f"Font Pair: {design.font_pair}")
    products = design.products
    if products:
        types = [p.product_type for p in products]
        parts.append(f"Product Types: {', '.join(types)}")
    if design.primary_product_type:
        parts.append(f"Primary Product Type: {design.primary_product_type}")
    if design.primary_product_type_reasoning:
        parts.append(f"Primary Product Reasoning: {design.primary_product_type_reasoning}")
    if design.trend:
        parts.append(f"Trend Source: {design.trend.source}")
        parts.append(f"Trend Signal: \"{design.trend.raw_signal}\"")
        if design.trend.claude_reasoning:
            parts.append(f"Trend Reasoning: {design.trend.claude_reasoning}")
    return "\n".join(parts)


def _generate_opening_message(design: Design) -> str:
    """Generate Claude's opening message for the chat drawer."""
    source_desc = ""
    if design.trend:
        source_map = {"google": "Google Trends", "reddit": "Reddit", "twitter": "Twitter/X", "seasonal": "the seasonal calendar"}
        source_desc = f" based on a signal from {source_map.get(design.trend.source, design.trend.source)}"
        if design.trend.raw_signal:
            source_desc += f" (\"{design.trend.raw_signal[:80]}\")"

    archetype_map = {
        "illustration": "a visual illustration",
        "hybrid": "a hybrid image-and-text design",
        "text_icon": "a text-with-icon design",
        "typographic": "a typography-focused design",
        "text_only": "a text-only design",
    }
    style_desc = archetype_map.get(design.archetype, f"a {design.archetype} design")

    parts = [f"I created \"{design.concept_name}\"{source_desc}."]
    parts.append(f"It's {style_desc} that scored {design.quality_score}/40 on quality.")

    if design.primary_text:
        parts.append(f"The main text reads: \"{design.primary_text}\".")

    parts.append("What would you like to change or explore?")

    return " ".join(parts)


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


@router.post("/preview-prompts")
def preview_product_prompts(
    concept: str,
    archetype: str = "illustration",
    niche: str = "",
    _: str = Depends(verify_api_key),
):
    """
    Generate and return format-specific prompts for ALL product types.
    Use this to review how prompts differ per product before running a batch.
    """
    from app.services.design.prompt_builder import preview_all_product_prompts
    results = preview_all_product_prompts(concept, archetype, niche, concept)
    return _envelope(results)


@router.post("/fix-classifications")
def fix_classifications(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """One-off: fix designs misclassified as 'collection' that have no collection_id."""
    updated = db.query(Design).filter(
        Design.classification == "collection",
        Design.collection_id == None,
        Design.is_deleted == False,
    ).update({Design.classification: "design_idea"}, synchronize_session=False)
    db.commit()
    return _envelope({"fixed": updated})


@router.post("/{design_id}/update-text")
def update_design_text(
    design_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
    primary_text: str | None = None,
    secondary_text: str | None = None,
    position: str = "center",
):
    """Update text fields and rerender preview in one call."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    if primary_text is not None:
        design.primary_text = primary_text
    if secondary_text is not None:
        design.secondary_text = secondary_text
    db.commit()

    if design.archetype in ("text_only", "typographic"):
        from app.services.design.text_preview import generate_text_preview
        from app.utils.storage import storage
        did = str(design.id)
        primary = design.primary_text or design.concept_name
        for dark in (True, False):
            img_bytes = generate_text_preview(
                primary_text=primary,
                secondary_text=design.secondary_text,
                font_pair=design.font_pair,
                dark_mode=dark,
                position=position,
            )
            path = storage.design_processed_path(did) if dark else storage.design_light_variant_path(did)
            url = storage.upload(path, img_bytes, "image/png")
            if dark:
                design.processed_image_url = url
        db.commit()

    return _envelope({
        "id": str(design_id),
        "primary_text": design.primary_text,
        "secondary_text": design.secondary_text,
    })


@router.post("/fix-poster-product-types")
def fix_poster_product_types(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """One-off: migrate designs with primary_product_type='poster' to 'tshirt'."""
    updated = db.query(Design).filter(
        Design.primary_product_type == "poster",
        Design.is_deleted == False,
    ).update(
        {
            Design.primary_product_type: "tshirt",
            Design.primary_product_type_reasoning: "Migrated from poster (removed product type)",
        },
        synchronize_session=False,
    )
    db.commit()
    return _envelope({"fixed": updated})


@router.post("/{design_id}/rerender-preview")
def rerender_preview(
    design_id: UUID,
    position: str = "center",
    primary_text: str | None = None,
    secondary_text: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Re-render a text_only/typographic design's preview image with optional text and position override."""
    design = db.query(Design).filter(Design.id == design_id, Design.is_deleted == False).first()
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")
    if design.archetype not in ("text_only", "typographic"):
        raise HTTPException(400, "Only text_only/typographic designs can be re-rendered")

    if primary_text is not None:
        design.primary_text = primary_text
    if secondary_text is not None:
        design.secondary_text = secondary_text

    from app.services.design.text_preview import generate_text_preview
    from app.utils.storage import storage

    primary = design.primary_text or design.concept_name
    did = str(design.id)

    dark_bytes = generate_text_preview(
        primary_text=primary,
        secondary_text=design.secondary_text,
        font_pair=design.font_pair,
        dark_mode=True,
        position=position,
    )
    processed_url = storage.upload(storage.design_processed_path(did), dark_bytes, "image/png")
    design.processed_image_url = processed_url

    light_bytes = generate_text_preview(
        primary_text=primary,
        secondary_text=design.secondary_text,
        font_pair=design.font_pair,
        dark_mode=False,
        position=position,
    )
    light_url = storage.upload(storage.design_light_variant_path(did), light_bytes, "image/png")

    db.commit()
    return _envelope({"id": str(design_id), "position": position, "processed_image_url": processed_url, "light_variant_url": light_url})


def _log_feedback(db, design: Design, action: str, edited_prompt: str = None):
    log = FeedbackLog(
        design_id=design.id,
        action=action,
        original_prompt=design.image_prompt or "",
        edited_prompt=edited_prompt,
        week=datetime.utcnow().date(),
    )
    db.add(log)
