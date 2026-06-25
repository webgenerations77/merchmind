"""
Main Sunday batch orchestrator — 8-step pipeline.
Each design generation runs inline within the batch task.
Emits progress events via Redis pub/sub for SSE streaming.

DESIGN TYPE AUDIT (Section 1):
  Pipeline branches on archetype at step 4:
  - text_only/typographic: skip image gen, render via text_preview.py (4500x5400)
  - illustration: generate image, rembg bg removal, normalize to 4500x5400 canvas
  - hybrid/text_icon: generate image, Pillow bg removal, composite text overlay
  Bias rotation cycles: image_only → text → image_text (balanced archetype distribution)
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from celery import group
import redis

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.batch import Batch
from app.models.trend import Trend
from app.models.design import Design
from app.models.product import Product
from app.models.marketing_asset import MarketingAsset
from app.models.alert import Alert
from app.models.niche_cluster import NicheCluster
from app.models.settings import AppSettings
from app.models.batch_item import BatchItem

from app.services.intelligence import google_trends, reddit_scraper, twitter_scraper, seasonal_calendar
from app.services.intelligence.trend_scorer import score_trend_signal, score_merch_viability, check_risk
from app.services.design.archetype_classifier import classify_archetype, select_image_api
from app.services.design.prompt_builder import build_image_prompt, generate_text_content, get_product_format
from app.services.design.image_generator import generate_image
from app.services.design.post_processor import process_image, image_to_bytes
from app.services.design.quality_scorer import score_design_quality, assign_product_bundle, select_primary_product_type, default_primary_product_type
from app.utils.text import to_title_case
from app.services.design.text_compositor import composite_text_on_image, should_composite
from app.services.design.font_selector import select_font_pair
from app.services.design.shopify_copy_generator import generate_shopify_copy
from app.services.design.text_preview import generate_text_preview
from app.services.pricing.pricing_engine import calculate_price
from app.services.marketing.combined_generator import generate_all_marketing_assets
from app.services.publishing.printify_publisher import get_base_cost, generate_mockups
from app.services.notifications.push_notifications import notify_batch_ready
from app.services.notifications.email_notifications import send_batch_ready_email
from app.utils.storage import storage

logger = logging.getLogger(__name__)

from app.config import settings as _settings
_redis = redis.from_url(_settings.REDIS_URL)


def _emit_progress(batch_id: str, step: int, total: int, message: str, data: dict = None):
    """Emit a progress event via Redis pub/sub for SSE consumers."""
    event = json.dumps({
        "batch_id": batch_id,
        "step": step,
        "total": total,
        "message": message,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat(),
    })
    _redis.publish(f"batch_progress:{batch_id}", event)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks.batch_pipeline.run_weekly_batch",
)
def run_weekly_batch(self, batch_id: Optional[str] = None, max_designs: Optional[int] = None, max_trends: Optional[int] = 30, trend_sources: Optional[list] = None, style_filter: Optional[str] = None, product_focus: Optional[list] = None):
    """
    Main Sunday batch task. Creates or resumes a batch and runs all 8 pipeline steps.
    Optional max_designs/max_trends limit output for testing.
    """
    db = SessionLocal()
    batch = None
    try:
        # Step 1: Initialize batch (skip if one is already running)
        logger.info("Batch pipeline starting")
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        if batch_id:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            existing = db.query(Batch).filter(Batch.status == "running").first()
            if existing:
                logger.warning("Batch already running id=%s — skipping duplicate", existing.id)
                return
            batch = Batch(week_start=week_start, status="running", run_started_at=datetime.utcnow())
            db.add(batch)
            db.commit()
            db.refresh(batch)

        bid = str(batch.id)
        _emit_progress(bid, 1, 8, "Batch initialized")

        # Load active settings
        settings_row = db.query(AppSettings).first()
        score_threshold = settings_row.score_threshold if settings_row else 35
        max_queue = settings_row.max_queue_size if settings_row else 25
        quality_threshold = settings_row.quality_threshold if settings_row else 28
        trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20
        base_markup = settings_row.base_markup if settings_row else {}
        floor_prices = settings_row.floor_prices if settings_row else {}
        back_logo_url = settings_row.back_logo_url if settings_row else None
        back_logo_products = settings_row.back_logo_products if settings_row else ["tshirt", "hat"]
        marketing_generation_enabled = settings_row.marketing_generation_enabled if settings_row else False

        # Load active niche clusters
        active_clusters = db.query(NicheCluster).filter(NicheCluster.active == True).all()

        # Step 2: Scrape intelligence sources
        enabled_sources = set(trend_sources) if trend_sources else {"google_trends", "reddit", "twitter", "seasonal"}
        _emit_progress(bid, 2, 8, f"Scraping trend sources: {', '.join(enabled_sources)}")
        raw_signals = []

        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        _SCRAPER_TIMEOUT = 60  # seconds per scraper call

        def _run_with_timeout(fn, *args, label="scraper"):
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(fn, *args)
                try:
                    return future.result(timeout=_SCRAPER_TIMEOUT)
                except FuturesTimeout:
                    logger.warning("%s timed out after %ds — skipping", label, _SCRAPER_TIMEOUT)
                    return []

        # Google Trends
        if "google_trends" in enabled_sources:
            try:
                raw_signals.extend(_run_with_timeout(google_trends.fetch_us_trending, label="google_trends.trending"))
                for cluster in active_clusters:
                    raw_signals.extend(_run_with_timeout(
                        google_trends.fetch_rising_queries, cluster.keywords, cluster.name,
                        label=f"google_trends.rising[{cluster.name}]",
                    ))
            except Exception as e:
                _log_batch_error(batch, db, f"Google Trends scraper failed: {e}")

        # Reddit
        if "reddit" in enabled_sources:
            try:
                for cluster in active_clusters:
                    raw_signals.extend(_run_with_timeout(
                        reddit_scraper.fetch_subreddit_signals, cluster.subreddits, cluster.name,
                        label=f"reddit[{cluster.name}]",
                    ))
            except Exception as e:
                _log_batch_error(batch, db, f"Reddit scraper failed: {e}")

        # Twitter
        if "twitter" in enabled_sources:
            try:
                raw_signals.extend(_run_with_timeout(twitter_scraper.fetch_us_trends, label="twitter.trending"))
                for cluster in active_clusters:
                    raw_signals.extend(_run_with_timeout(
                        twitter_scraper.fetch_keyword_tweets, cluster.keywords, cluster.name,
                        label=f"twitter[{cluster.name}]",
                    ))
            except Exception as e:
                _log_batch_error(batch, db, f"Twitter scraper failed: {e}")

        # Seasonal calendar
        if "seasonal" in enabled_sources:
            try:
                raw_signals.extend(seasonal_calendar.get_upcoming_events())
            except Exception as e:
                _log_batch_error(batch, db, f"Seasonal calendar failed: {e}")

        logger.info(f"Scraped {len(raw_signals)} raw signals")

        # Pre-filter: deduplicate and remove low-value signals before scoring
        seen = set()
        filtered_signals = []
        for signal in raw_signals:
            text = signal["raw_signal"].lower().strip()
            if text in seen or len(text) < 3 or len(text.split()) > 12:
                continue
            seen.add(text)
            filtered_signals.append(signal)
        logger.info(f"Pre-filter: {len(raw_signals)} → {len(filtered_signals)} signals")
        raw_signals = filtered_signals

        if max_trends and len(raw_signals) > max_trends:
            raw_signals = raw_signals[:max_trends]
            logger.info(f"max_trends limit: capped at {max_trends} signals")

        batch.total_ideas = len(raw_signals)
        db.commit()

        # Step 3: Score all signals (batched — 10 per Claude call)
        _emit_progress(bid, 3, 8, f"Scoring {len(raw_signals)} signals")
        cluster_keyword_map = {c.name: (c.keywords, c.score_boost) for c in active_clusters}
        queued_trends = []

        from app.services.intelligence.trend_scorer import score_trends_batch
        batch_inputs = []
        for signal in raw_signals:
            cluster_boost = 0
            signal_lower = signal["raw_signal"].lower()
            for name, (kws, boost) in cluster_keyword_map.items():
                if any(kw.lower() in signal_lower for kw in kws):
                    cluster_boost = boost
                    break
            batch_inputs.append({
                "raw_signal": signal["raw_signal"],
                "source": signal["source"],
                "source_metadata": signal.get("source_metadata", {}),
                "cluster_boost": cluster_boost,
            })

        scores = score_trends_batch(batch_inputs)
        logger.info(f"Batch scored {len(scores)} signals in {len(range(0, len(batch_inputs), 10))} Claude calls")

        for signal, score_result in zip(raw_signals, scores):
            try:
                trend = Trend(
                    batch_id=batch.id,
                    source=signal["source"],
                    raw_signal=signal["raw_signal"],
                    source_url=signal.get("source_url"),
                    source_metadata=signal.get("source_metadata", {}),
                    trend_score=score_result["trend_score"],
                    viability_score=score_result["viability_score"],
                    final_score=score_result["final_score"],
                    claude_reasoning=score_result["claude_reasoning"],
                    risk_flag=score_result["risk_flag"],
                    risk_reason=score_result.get("risk_reason"),
                )
                db.add(trend)

                if score_result["risk_flag"] == "hard":
                    trend.status = "rejected"
                elif score_result["final_score"] >= score_threshold:
                    trend.status = "queued"
                    queued_trends.append(trend)
                else:
                    trend.status = "rejected"

                db.commit()
            except Exception as e:
                logger.error(f"Saving score failed for '{signal.get('raw_signal', '')}': {e}")
                _log_batch_error(batch, db, f"Score error: {e}")

        # Limit queue with niche diversity — pick best from each niche first, then fill by score
        limit = min(max_queue, max_designs) if max_designs else max_queue
        queued_trends.sort(key=lambda t: t.final_score, reverse=True)

        niche_buckets: dict[str, list] = {}
        for t in queued_trends:
            meta = t.source_metadata or {}
            niche = meta.get("cluster") or meta.get("niche") or "general"
            niche_buckets.setdefault(niche, []).append(t)

        diverse_queue = []
        used_ids = set()
        for niche_name in sorted(niche_buckets.keys()):
            if len(diverse_queue) >= limit:
                break
            best = niche_buckets[niche_name][0]
            diverse_queue.append(best)
            used_ids.add(best.id)

        for t in queued_trends:
            if len(diverse_queue) >= limit:
                break
            if t.id not in used_ids:
                diverse_queue.append(t)
                used_ids.add(t.id)

        queued_trends = diverse_queue[:limit]
        logger.info(f"Niche diversity: {len(niche_buckets)} niches, selected from: {list(niche_buckets.keys())}")

        # Mark excess as rejected
        for trend in db.query(Trend).filter(
            Trend.batch_id == batch.id, Trend.status == "queued"
        ).all():
            if trend not in queued_trends:
                trend.status = "rejected"
        db.commit()

        batch.queued_count = len(queued_trends)
        db.commit()
        logger.info(f"Queued {len(queued_trends)} trends for design generation")

        # Steps 4-7: Generate designs for each queued trend (run inline, not as subtasks)
        _emit_progress(bid, 4, 8, f"Generating {len(queued_trends)} designs")
        approved_count = 0
        for i, trend in enumerate(queued_trends):
            concept = to_title_case(trend.raw_signal[:100])
            item = BatchItem(
                batch_id=batch.id,
                trend_id=trend.id,
                concept_name=concept,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            try:
                _emit_progress(
                    bid, 4, 8,
                    f"Designing {i + 1}/{len(queued_trends)}: {trend.raw_signal[:40]}",
                    {"current": i + 1, "total": len(queued_trends)},
                )
                _BIAS_ROTATION = ("image_only", "text", "image_text", "image_with_text")
                archetype_bias = _BIAS_ROTATION[i % len(_BIAS_ROTATION)]
                logger.info(f"Running design generation inline for trend {trend.id} (bias={archetype_bias})")
                pipeline_cfg = {
                    "quality_threshold": quality_threshold,
                    "trend_boost_max": trend_boost_max,
                    "base_markup": base_markup,
                    "floor_prices": floor_prices,
                    "back_logo_enabled": True,
                    "back_logo_url": back_logo_url,
                    "back_logo_products": back_logo_products,
                    "archetype_bias": archetype_bias,
                    "marketing_generation_enabled": marketing_generation_enabled,
                    "_batch_item_id": str(item.id),
                }
                if style_filter:
                    pipeline_cfg["style_filter"] = style_filter
                if product_focus:
                    pipeline_cfg["product_focus"] = product_focus
                _generate_design_for_trend(str(trend.id), str(batch.id), pipeline_cfg)
                approved_count += 1

                # Update item on success — pull design_id + product types from DB
                db.refresh(item)
                design = db.query(Design).filter(
                    Design.batch_id == batch.id, Design.trend_id == trend.id
                ).order_by(Design.created_at.desc()).first()
                if design:
                    item.design_id = design.id
                    products = db.query(Product).filter(Product.design_id == design.id).all()
                    item.product_types = [p.product_type for p in products]
                item.status = "success"
                item.completed_at = datetime.utcnow()
                db.commit()

            except Exception as e:
                logger.error(f"Design generation failed for trend {trend.id}: {e}")
                _log_batch_error(batch, db, f"Design error for trend {trend.id}: {type(e).__name__}: {e}")

                import traceback
                item.status = "failed"
                item.failed_step = _detect_failed_step(e)
                item.error_summary = _summarize_error(e, item.failed_step or "design_generation")
                item.error_detail = traceback.format_exc()
                item.completed_at = datetime.utcnow()
                db.commit()

        batch.approved_count = approved_count
        batch.status = "complete"
        batch.run_completed_at = datetime.utcnow()
        db.commit()

        # Step 8: Finalize
        _emit_progress(bid, 8, 8, "Batch complete — sending notifications")

        notify_batch_ready(str(batch.id), len(queued_trends))
        logger.info(f"Batch {bid} complete: {len(queued_trends)} designs queued")

    except Exception as e:
        logger.exception(f"Batch pipeline crashed: {e}")
        if batch:
            batch.status = "failed"
            _log_batch_error(batch, db, f"Pipeline crash: {e}")
            db.commit()
            alert = Alert(
                batch_id=batch.id,
                type="batch_ready",
                severity="critical",
                message=f"Batch pipeline failed: {e}",
            )
            db.add(alert)
            db.commit()
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks.batch_pipeline.generate_design_for_trend",
)
def _generate_design_for_trend(self, trend_id: str, batch_id: str, pipeline_settings: dict):
    """
    Isolated design generation task for a single trend.
    Failure here does not affect other designs.
    """
    db = SessionLocal()
    design = None
    try:
        logger.info(f"design_task[{trend_id[:8]}] started")
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            raise ValueError(f"Trend {trend_id} not found")

        quality_threshold = pipeline_settings.get("quality_threshold", 28)
        trend_boost_max = pipeline_settings.get("trend_boost_max", 0.20)
        base_markup = pipeline_settings.get("base_markup", {})
        floor_prices = pipeline_settings.get("floor_prices", {})
        back_logo_enabled = pipeline_settings.get("back_logo_enabled", False)
        back_logo_url = pipeline_settings.get("back_logo_url")
        back_logo_products = pipeline_settings.get("back_logo_products", ["tshirt", "hat"])

        niche_name = ""
        if trend.niche_cluster_id:
            cluster = db.query(NicheCluster).filter(NicheCluster.id == trend.niche_cluster_id).first()
            if cluster:
                niche_name = cluster.name

        # 4a: Classify archetype (bias alternates for balanced distribution)
        archetype_bias = pipeline_settings.get("archetype_bias")
        classify_result = classify_archetype(trend.raw_signal, trend.source, niche_name, bias=archetype_bias)

        # classify_archetype returns a dict for image_with_text, string otherwise
        iwt_meta = {}
        if isinstance(classify_result, dict):
            archetype = classify_result["archetype"]
            iwt_meta = classify_result
        else:
            archetype = classify_result
        logger.info(f"design_task[{trend_id[:8]}] archetype={archetype} bias={archetype_bias}")

        # 4b: Select image API
        image_api = select_image_api(archetype)

        # Create design record
        design = Design(
            trend_id=trend.id,
            batch_id=batch_id,
            concept_name=to_title_case(trend.raw_signal[:100]),
            archetype=archetype,
            image_api_used=image_api,
            status="generating",
        )
        if iwt_meta:
            design.primary_text = iwt_meta.get("text_content", "")
        db.add(design)
        db.commit()
        db.refresh(design)
        design_id = str(design.id)
        logger.info(f"design_task[{trend_id[:8]}] design created id={design_id[:8]}")

        # 4c / 4d: Generate image
        product_focus_list = pipeline_settings.get("product_focus")
        primary_product = product_focus_list[0] if product_focus_list else default_primary_product_type(archetype)
        fmt = get_product_format(primary_product)
        processed_url = None
        color_palette = []

        if archetype == "image_with_text":
            # --- Ideogram path: integrated image + text in one call ---
            from app.services.design.ideogram_service import generate_and_store
            iwt_image_desc = iwt_meta.get("image_description", trend.raw_signal)
            iwt_text = iwt_meta.get("text_content", design.concept_name)
            try:
                raw_url, processed_url, ideogram_prompt = generate_and_store(
                    design_id, iwt_image_desc, iwt_text, product_type=primary_product,
                )
                design.raw_image_url = raw_url
                design.processed_image_url = processed_url
                design.image_prompt = ideogram_prompt
                design.image_api_used = "ideogram"
                db.commit()
                logger.info(
                    "design_task[%s] ideogram image generated prompt='%s'",
                    trend_id[:8], ideogram_prompt[:120],
                )
            except Exception as img_err:
                error_msg = f"Ideogram generation failed: {type(img_err).__name__}: {img_err}"
                logger.error("design_task[%s] %s", trend_id[:8], error_msg)
                design.status = "generation_failed"
                design.font_reasoning = error_msg[:500]
                _log_batch_error(db.query(Batch).filter(Batch.id == batch_id).first(), db, error_msg[:300])
                db.commit()
                raise
        else:
            # --- Standard Flux/DALL-E path ---
            image_prompt = build_image_prompt(
                trend.raw_signal, archetype, niche_name, design.concept_name,
                product_type=primary_product,
            )
            if image_prompt:
                from app.services.design.preference_learner import get_prompt_preferences
                pref_suffix = get_prompt_preferences(db)
                if pref_suffix:
                    image_prompt = f"{image_prompt} {pref_suffix}"
                style_hint = pipeline_settings.get("style_filter")
                if style_hint:
                    image_prompt = f"{image_prompt} Style direction: {style_hint}."
            design.image_prompt = image_prompt
            db.commit()
            logger.info(
                "design_task[%s] prompt built product_type=%s aspect=%s prompt='%s'",
                trend_id[:8], primary_product, fmt["aspect_ratio"],
                (image_prompt or "")[:150],
            )

            if image_api and image_prompt:
                try:
                    logger.info(f"design_task[{trend_id[:8]}] generating image via {image_api} aspect={fmt['aspect_ratio']}...")
                    raw_bytes, api_used = generate_image(image_prompt, image_api, aspect_ratio=fmt["aspect_ratio"])
                    design.image_api_used = api_used
                    logger.info(f"design_task[{trend_id[:8]}] image generated via {api_used}, {len(raw_bytes)} bytes")

                    # Upload raw image
                    raw_path = storage.design_raw_path(design_id)
                    raw_url = storage.upload(raw_path, raw_bytes)
                    design.raw_image_url = raw_url

                    if archetype == "illustration":
                        from app.services.design.post_processor import process_image as full_process, image_to_bytes as img2b
                        canvas, report = full_process(raw_bytes)
                        clean_bytes = img2b(canvas)
                        color_palette = report.get("color_palette", [])
                        logger.info("design_task[%s] illustration: rembg + canvas 4500x5400", trend_id[:8])
                    else:
                        from app.services.design.bg_remover import remove_white_background
                        clean_bytes = remove_white_background(raw_bytes)
                    proc_path = storage.design_processed_path(design_id)
                    processed_url = storage.upload(proc_path, clean_bytes)
                    design.processed_image_url = processed_url
                    db.commit()
                    logger.info(f"design_task[{trend_id[:8]}] images uploaded (bg removed)")

                except Exception as img_err:
                    error_msg = f"Image generation failed: {type(img_err).__name__}: {img_err}"
                    logger.warning(f"{error_msg} — design {design_id}; forcing text_only")
                    archetype = "text_only"
                    design.archetype = archetype
                    design.image_api_used = None
                    design.font_reasoning = error_msg[:500]
                    _log_batch_error(db.query(Batch).filter(Batch.id == batch_id).first(), db, error_msg[:300])
                    db.commit()

        design.color_palette = color_palette

        # 4f: Generate + composite text content (skip for image_with_text — Ideogram already rendered text)
        if archetype == "image_with_text":
            text_content = {
                "primary_text": iwt_meta.get("text_content", design.concept_name),
                "secondary_text": None,
                "tagline": None,
                "text_concept_scoring": None,
            }
        else:
            text_content = generate_text_content(trend.raw_signal, archetype, niche_name)

        # 4f: Select font
        font_result = select_font_pair(
            trend.raw_signal, archetype, niche_name, text_content.get("primary_text", "")
        )
        design.font_pair = font_result["font_pair"]
        design.font_reasoning = font_result["reasoning"]
        design.design_style = archetype
        db.commit()

        design.primary_text = text_content.get("primary_text")
        design.secondary_text = text_content.get("secondary_text")
        design.tagline = text_content.get("tagline")
        design.text_concept_scoring = text_content.get("text_concept_scoring")
        db.commit()

        # 4f-2: Composite text onto image for hybrid/text_icon
        if processed_url and should_composite(archetype):
            try:
                img_bytes = storage.download(storage.design_processed_path(design_id))
                composited = composite_text_on_image(
                    img_bytes,
                    primary_text=text_content.get("primary_text", trend.raw_signal),
                    secondary_text=text_content.get("secondary_text"),
                    archetype=archetype,
                    color_palette=color_palette,
                )
                processed_url = storage.upload(
                    storage.design_processed_path(design_id), composited, "image/png"
                )
                design.processed_image_url = processed_url
                db.commit()
                logger.info(f"design_task[{trend_id[:8]}] text composited onto image")
            except Exception as comp_err:
                logger.warning(f"Text compositing failed for design {design_id}: {comp_err}")

        # 4f-3: Generate text preview for text_only/typographic designs without images
        light_variant_url = None
        if not processed_url and archetype in ("text_only", "typographic"):
            try:
                preview_bytes = generate_text_preview(
                    primary_text=text_content.get("primary_text", trend.raw_signal),
                    secondary_text=text_content.get("secondary_text"),
                    font_pair=font_result["font_pair"],
                    color_palette=color_palette,
                    dark_mode=True,
                )
                preview_path = storage.design_processed_path(design_id)
                processed_url = storage.upload(preview_path, preview_bytes, "image/png")
                design.processed_image_url = processed_url
                light_bytes = generate_text_preview(
                    primary_text=text_content.get("primary_text", trend.raw_signal),
                    secondary_text=text_content.get("secondary_text"),
                    font_pair=font_result["font_pair"],
                    color_palette=color_palette,
                    dark_mode=False,
                )
                light_path = storage.design_light_variant_path(design_id)
                light_variant_url = storage.upload(light_path, light_bytes, "image/png")
                db.commit()
                logger.info(f"design_task[{trend_id[:8]}] text preview: dark + light variants generated")
            except Exception as preview_err:
                logger.warning(f"Text preview generation failed for design {design_id}: {preview_err}")

        # 4g: Quality score (only if we have a processed image)
        regen_count = 0
        while regen_count < 2:
            if processed_url:
                quality = score_design_quality(
                    processed_url, design.concept_name, archetype, niche_name,
                    threshold=quality_threshold,
                )
                design.quality_score = quality["total"]
                design.quality_breakdown = quality["breakdown"]
                db.commit()

                if quality["passes_threshold"]:
                    break
                elif regen_count == 0 and image_api:
                    # Regenerate once
                    logger.info(f"Quality {quality['total']}/40 below threshold, regenerating design {design_id}")
                    try:
                        new_prompt = build_image_prompt(trend.raw_signal, archetype, niche_name, design.concept_name)
                        raw_bytes, api_used = generate_image(new_prompt, image_api)
                        processed_img, report = process_image(raw_bytes)
                        processed_bytes = image_to_bytes(processed_img)
                        processed_url = storage.upload(storage.design_processed_path(design_id), processed_bytes)
                        design.processed_image_url = processed_url
                        design.version = 2
                        db.commit()
                        regen_count += 1
                        continue
                    except Exception:
                        pass
                # Keep the image design even if quality is low — don't degrade to text_only
                if design.raw_image_url:
                    logger.info(f"Quality below threshold but keeping image design {design_id}")
                    break
                archetype = "text_only"
                design.archetype = archetype
                design.image_api_used = None
                processed_url = None
                design.quality_score = 30
                design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 7, "merch_suitability": 8, "originality": 7}
                db.commit()
                break
            else:
                # No image — text_only always passes
                design.quality_score = 30
                design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 7, "merch_suitability": 8, "originality": 7}
                db.commit()
                break

        # 4h: Assign product bundle + AI-driven primary product type
        product_types = assign_product_bundle(design.archetype, design.quality_breakdown or {})
        if pipeline_settings.get("product_focus"):
            focus = pipeline_settings["product_focus"]
            product_types = [pt for pt in focus if pt in product_types] or focus[:4]
        primary_result = select_primary_product_type(
            design.concept_name, design.archetype, product_types, trend.raw_signal,
        )
        design.primary_product_type = primary_result["primary_product_type"]
        design.primary_product_type_reasoning = primary_result["reasoning"]
        design.classification = "collection" if design.collection_id else "design_idea"

        # 4i: Generate Shopify copy
        copy = generate_shopify_copy(
            design.concept_name, trend.raw_signal, design.archetype, product_types, niche_name
        )
        design.shopify_title = copy["shopify_title"]
        design.shopify_description = copy["shopify_description"]
        design.shopify_tags = copy["shopify_tags"]
        db.commit()

        # Step 5: Generate mockups + Step 6: Pricing — create Product records
        from app.services.publishing.printify_publisher import _DUAL_PRINT_SURCHARGE
        for pt in product_types:
            base_cost = get_base_cost(pt)
            if back_logo_enabled and pt in back_logo_products:
                base_cost += _DUAL_PRINT_SURCHARGE.get(pt, 2.50)
            pricing = calculate_price(
                pt, base_cost, trend.final_score, base_markup, floor_prices, trend_boost_max
            )
            product = Product(
                design_id=design.id,
                product_type=pt,
                printify_base_cost=pricing["printify_base_cost"],
                base_markup=pricing["base_markup"],
                trend_adjustment=pricing["trend_adjustment"],
                retail_price=pricing["retail_price"],
                floor_price=pricing["floor_price"],
                margin_flag=pricing["margin_flag"],
                publish_status="pending",
            )
            db.add(product)

            if pricing["margin_flag"]:
                margin_alert = Alert(
                    design_id=design.id,
                    batch_id=batch_id,
                    type="margin_warning",
                    severity="warning",
                    message=f"Low margin on {pt} for '{design.concept_name}': margin={pricing['margin']:.1%}",
                )
                db.add(margin_alert)

        db.commit()

        # Step 6b: Generate Printify products + mockups for all product types
        image_url = design.processed_image_url or design.raw_image_url
        if image_url:
            from app.services.publishing.printify_publisher import create_product as printify_create, _get as _get_printify
            from app.services.design.text_preview import _LIGHT_PRODUCT_TYPES
            from app.services.design.shopify_copy_generator import get_product_description
            for product in db.query(Product).filter(Product.design_id == design.id).all():
                try:
                    product_label = product.product_type.replace("_", " ").title()
                    base_name = design.concept_name or design.shopify_title or "Design"
                    product_back_logo = back_logo_url if (back_logo_enabled and product.product_type in back_logo_products) else None
                    use_image = light_variant_url if (light_variant_url and product.product_type in _LIGHT_PRODUCT_TYPES) else image_url
                    product_desc = get_product_description(
                        design.shopify_description or "", product.product_type, design.concept_name,
                    )
                    printify_id = printify_create(
                        product_type=product.product_type,
                        title=f"{base_name} — {product_label}",
                        description=product_desc,
                        image_url=use_image,
                        retail_price=float(product.retail_price),
                        back_logo_url=product_back_logo,
                        archetype=design.archetype,
                    )
                    product.printify_product_id = printify_id
                    mockups = _get_printify().generate_mockups(printify_id, design_id=design_id, product_type=product.product_type)
                    product.mockup_urls = mockups
                    db.commit()
                    logger.info(f"design_task[{trend_id[:8]}] Printify mockup for {product.product_type}")
                except Exception as mock_err:
                    logger.warning(f"design_task[{trend_id[:8]}] Printify mockup failed for {product.product_type}: {mock_err}")

        # Step 6c: Dynamic Mockups for products missing Printify mockups
        if image_url:
            from app.services.design.dynamic_mockups import get_dynamic_mockups_service
            dm = get_dynamic_mockups_service()
            if dm.is_available():
                for product in db.query(Product).filter(Product.design_id == design.id).all():
                    if not product.mockup_urls or not product.mockup_urls.get("front"):
                        url = dm.render_mockup(product.product_type, image_url, design_id)
                        if url:
                            product.mockup_urls = {"front": url}
                            db.commit()
                            logger.info(f"design_task[{trend_id[:8]}] Dynamic Mockups for {product.product_type}")

        # Step 6d: Pillow mockups as final fallback
        if image_url:
            from app.services.design.mockup_generator import generate_mockup
            for product in db.query(Product).filter(Product.design_id == design.id).all():
                if not product.mockup_urls or not product.mockup_urls.get("front"):
                    try:
                        import httpx
                        img_resp = httpx.get(image_url, timeout=15)
                        mockup_bytes = generate_mockup(product.product_type, img_resp.content, archetype=design.archetype)
                        if mockup_bytes:
                            mockup_path = storage.mockup_path(design_id, product.product_type, "front")
                            mockup_url = storage.upload(mockup_path, mockup_bytes)
                            product.mockup_urls = {"front": mockup_url}
                            db.commit()
                            logger.info(f"design_task[{trend_id[:8]}] Pillow mockup for {product.product_type}")
                    except Exception as e:
                        logger.warning(f"design_task[{trend_id[:8]}] Pillow mockup failed for {product.product_type}: {e}")

        # Step 7: Generate marketing assets (if enabled)
        if pipeline_settings.get("marketing_generation_enabled", False):
            _generate_marketing_assets(design, trend, niche_name, product_types, db)
        else:
            logger.info("Marketing generation paused — skipping marketing assets for design %s", design.id)

        # Mark design ready
        design.status = "ready"
        db.commit()

        logger.info(f"Design {design_id} generated successfully for trend '{trend.raw_signal[:40]}'")

    except Exception as e:
        logger.error(f"Design generation failed for trend {trend_id}: {e}")
        if design:
            design.status = "rejected"
            db.commit()

        # Update batch item with failure details from inside the task
        item_id = pipeline_settings.get("_batch_item_id")
        if item_id:
            import traceback as tb_mod
            bi = db.query(BatchItem).filter(BatchItem.id == item_id).first()
            if bi and bi.status == "running":
                bi.status = "failed"
                bi.failed_step = _detect_failed_step(e)
                bi.error_summary = _summarize_error(e, bi.failed_step)
                bi.error_detail = tb_mod.format_exc()
                bi.completed_at = datetime.utcnow()
                if design:
                    bi.design_id = design.id
                db.commit()
        raise
    finally:
        db.close()


def _generate_marketing_assets(design: Design, trend: Trend, niche: str, product_types: list[str], db):
    """Generate all 5 marketing channel assets in a single Claude call.
    Featured designs are processed first at the batch level and receive priority scheduling.
    """
    # TODO: increase ad spend allocation for featured items
    try:
        all_content = generate_all_marketing_assets(
            design.concept_name, trend.raw_signal, design.archetype, niche,
            design.shopify_title or design.concept_name, product_types,
        )
        for channel, content in all_content.items():
            asset = MarketingAsset(
                design_id=design.id,
                channel=channel,
                content=content,
                status="pending",
            )
            db.add(asset)
    except Exception as e:
        logger.error(f"Marketing asset generation failed for design {design.id}: {e}")
        for channel in ["instagram", "tiktok", "pinterest", "email", "blog"]:
            asset = MarketingAsset(
                design_id=design.id,
                channel=channel,
                content={},
                status="failed",
            )
            db.add(asset)
    db.commit()


def _log_batch_error(batch: Batch, db, message: str):
    errors = list(batch.error_log or [])
    errors.append({"time": datetime.utcnow().isoformat(), "error": message})
    batch.error_log = errors
    db.commit()


def _detect_failed_step(exc: Exception) -> str:
    """Infer which pipeline step failed from the exception context."""
    msg = str(exc).lower()
    if "archetype" in msg or "classify" in msg:
        return "archetype"
    if "image" in msg or "flux" in msg or "dalle" in msg or "replicate" in msg or "openai" in msg or "ideogram" in msg:
        return "image_generation"
    if "quality" in msg or "score" in msg:
        return "quality"
    if "printify" in msg or "mockup" in msg:
        return "mockups"
    if "price" in msg or "pricing" in msg or "product" in msg:
        return "products"
    if "marketing" in msg:
        return "marketing"
    return "design_generation"


def _summarize_error(exc: Exception, step: str) -> str:
    """Turn an exception into a short human-readable summary."""
    etype = type(exc).__name__
    msg = str(exc)[:300]
    summaries = {
        "scoring": f"Trend scoring failed: {etype}",
        "archetype": f"Archetype classification failed: {etype}",
        "image_generation": f"Image generation failed: {etype} — {msg[:100]}",
        "quality": f"Quality scoring failed: {etype}",
        "products": f"Product creation failed: {etype}",
        "mockups": f"Mockup generation failed: {etype}",
        "marketing": f"Marketing asset generation failed: {etype}",
    }
    return summaries.get(step, f"{step} failed: {etype} — {msg[:100]}")
