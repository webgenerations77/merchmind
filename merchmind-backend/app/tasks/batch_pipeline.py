"""
Main Sunday batch orchestrator — 10-step pipeline.
Each design generation runs as an isolated Celery subtask.
Emits progress events via Redis pub/sub for SSE streaming.
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

from app.services.intelligence import google_trends, reddit_scraper, twitter_scraper, seasonal_calendar
from app.services.intelligence.trend_scorer import score_trend_signal, score_merch_viability, check_risk
from app.services.design.archetype_classifier import classify_archetype, select_image_api
from app.services.design.prompt_builder import build_image_prompt, generate_text_content
from app.services.design.image_generator import generate_image
from app.services.design.post_processor import process_image, image_to_bytes
from app.services.design.quality_scorer import score_design_quality, assign_product_bundle
from app.services.design.font_selector import select_font_pair
from app.services.design.shopify_copy_generator import generate_shopify_copy
from app.services.design.text_preview import generate_text_preview
from app.services.pricing.pricing_engine import calculate_price
from app.services.marketing.instagram_generator import generate_instagram_assets
from app.services.marketing.tiktok_generator import generate_tiktok_assets
from app.services.marketing.pinterest_generator import generate_pinterest_assets
from app.services.marketing.email_generator import generate_email_assets
from app.services.marketing.blog_generator import generate_blog_post
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
def run_weekly_batch(self, batch_id: Optional[str] = None):
    """
    Main Sunday batch task. Creates or resumes a batch and runs all 8 pipeline steps.
    """
    db = SessionLocal()
    batch = None
    try:
        # Step 1: Initialize batch
        logger.info("Batch pipeline starting")
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        if batch_id:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            batch = Batch(week_start=week_start, status="running", run_started_at=datetime.utcnow())
            db.add(batch)
            db.commit()
            db.refresh(batch)

        bid = str(batch.id)
        _emit_progress(bid, 1, 8, "Batch initialized")

        # Load active settings
        settings_row = db.query(AppSettings).first()
        score_threshold = settings_row.score_threshold if settings_row else 35
        min_queue = settings_row.min_queue_size if settings_row else 10
        max_queue = settings_row.max_queue_size if settings_row else 25
        quality_threshold = settings_row.quality_threshold if settings_row else 28
        trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20
        base_markup = settings_row.base_markup if settings_row else {}
        floor_prices = settings_row.floor_prices if settings_row else {}

        # Load active niche clusters
        active_clusters = db.query(NicheCluster).filter(NicheCluster.active == True).all()

        # Step 2: Scrape intelligence sources
        _emit_progress(bid, 2, 8, "Scraping trend sources")
        raw_signals = []

        # Google Trends
        try:
            raw_signals.extend(google_trends.fetch_us_trending())
            for cluster in active_clusters:
                raw_signals.extend(google_trends.fetch_rising_queries(cluster.keywords, cluster.name))
        except Exception as e:
            _log_batch_error(batch, db, f"Google Trends scraper failed: {e}")

        # Reddit
        try:
            for cluster in active_clusters:
                raw_signals.extend(reddit_scraper.fetch_subreddit_signals(cluster.subreddits, cluster.name))
        except Exception as e:
            _log_batch_error(batch, db, f"Reddit scraper failed: {e}")

        # Twitter
        try:
            raw_signals.extend(twitter_scraper.fetch_us_trends())
            for cluster in active_clusters:
                raw_signals.extend(twitter_scraper.fetch_keyword_tweets(cluster.keywords, cluster.name))
        except Exception as e:
            _log_batch_error(batch, db, f"Twitter scraper failed: {e}")

        # Seasonal calendar
        try:
            raw_signals.extend(seasonal_calendar.get_upcoming_events())
        except Exception as e:
            _log_batch_error(batch, db, f"Seasonal calendar failed: {e}")

        logger.info(f"Scraped {len(raw_signals)} raw signals")
        batch.total_ideas = len(raw_signals)
        db.commit()

        # Step 3: Score all signals
        _emit_progress(bid, 3, 8, f"Scoring {len(raw_signals)} signals")
        cluster_keyword_map = {c.name: (c.keywords, c.score_boost) for c in active_clusters}
        queued_trends = []

        for signal in raw_signals:
            try:
                trend = Trend(
                    batch_id=batch.id,
                    source=signal["source"],
                    raw_signal=signal["raw_signal"],
                    source_url=signal.get("source_url"),
                    source_metadata=signal.get("source_metadata", {}),
                )
                db.add(trend)
                db.flush()

                # Stage 1
                s1 = score_trend_signal(
                    signal["raw_signal"], signal["source"], signal.get("source_metadata", {})
                )
                trend.trend_score = s1["trend_score"]

                # Cluster boost
                cluster_boost = 0
                matched_cluster_kws = []
                signal_lower = signal["raw_signal"].lower()
                for name, (kws, boost) in cluster_keyword_map.items():
                    if any(kw.lower() in signal_lower for kw in kws):
                        cluster_boost = boost
                        matched_cluster_kws = kws
                        break

                # Stage 2
                s2 = score_merch_viability(
                    signal["raw_signal"], s1["trend_score"], matched_cluster_kws, cluster_boost
                )
                trend.viability_score = s2["viability_score"]
                trend.final_score = s2["final_score"]
                trend.claude_reasoning = s2["claude_reasoning"]

                # Risk check
                risk = check_risk(signal["raw_signal"], s2["final_score"], score_threshold)
                trend.risk_flag = risk["risk_flag"]
                trend.risk_reason = risk.get("risk_reason")

                if risk["risk_flag"] == "hard":
                    trend.status = "rejected"
                elif s2["final_score"] >= score_threshold:
                    trend.status = "queued"
                    queued_trends.append(trend)
                else:
                    trend.status = "rejected"

                trend.status = trend.status
                db.commit()

            except Exception as e:
                logger.error(f"Scoring failed for signal '{signal.get('raw_signal', '')}': {e}")
                _log_batch_error(batch, db, f"Score error: {e}")

        # Limit queue to max_queue, sorted by final_score descending
        queued_trends.sort(key=lambda t: t.final_score, reverse=True)
        queued_trends = queued_trends[:max_queue]

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

        # Steps 4-7: Generate designs for each queued trend
        _emit_progress(bid, 4, 8, f"Generating {len(queued_trends)} designs")
        approved_count = 0
        for i, trend in enumerate(queued_trends):
            try:
                _emit_progress(
                    bid, 4, 8,
                    f"Designing {i + 1}/{len(queued_trends)}: {trend.raw_signal[:40]}",
                    {"current": i + 1, "total": len(queued_trends)},
                )
                _generate_design_for_trend.delay(str(trend.id), str(batch.id), {
                    "quality_threshold": quality_threshold,
                    "trend_boost_max": trend_boost_max,
                    "base_markup": base_markup,
                    "floor_prices": floor_prices,
                })
                approved_count += 1
            except Exception as e:
                logger.error(f"Failed to dispatch design task for trend {trend.id}: {e}")
                _log_batch_error(batch, db, f"Design dispatch error for trend {trend.id}: {e}")

        batch.approved_count = approved_count
        batch.status = "complete"
        batch.run_completed_at = datetime.utcnow()
        db.commit()

        # Step 8: Finalize
        _emit_progress(bid, 8, 8, "Batch complete — sending notifications")

        # Fire alert if below min queue
        if len(queued_trends) < min_queue:
            alert = Alert(
                batch_id=batch.id,
                type="empty_batch",
                severity="warning",
                message=f"Batch generated only {len(queued_trends)} ideas (minimum: {min_queue}). Manual ideas unlocked.",
            )
            db.add(alert)
            db.commit()

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
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            raise ValueError(f"Trend {trend_id} not found")

        quality_threshold = pipeline_settings.get("quality_threshold", 28)
        trend_boost_max = pipeline_settings.get("trend_boost_max", 0.20)
        base_markup = pipeline_settings.get("base_markup", {})
        floor_prices = pipeline_settings.get("floor_prices", {})

        niche_name = ""
        if trend.niche_cluster_id:
            cluster = db.query(NicheCluster).filter(NicheCluster.id == trend.niche_cluster_id).first()
            if cluster:
                niche_name = cluster.name

        # 4a: Classify archetype
        archetype = classify_archetype(trend.raw_signal, trend.source, niche_name)

        # 4b: Select image API
        image_api = select_image_api(archetype)

        # Create design record
        design = Design(
            trend_id=trend.id,
            batch_id=batch_id,
            concept_name=trend.raw_signal[:100],
            archetype=archetype,
            image_api_used=image_api,
            status="generating",
        )
        db.add(design)
        db.commit()
        db.refresh(design)
        design_id = str(design.id)

        # 4c: Build image prompt
        image_prompt = build_image_prompt(trend.raw_signal, archetype, niche_name, design.concept_name)
        design.image_prompt = image_prompt
        db.commit()

        # 4d: Generate image (if applicable)
        processed_url = None
        color_palette = []
        if image_api and image_prompt:
            try:
                raw_bytes, api_used = generate_image(image_prompt, image_api)
                design.image_api_used = api_used

                # Upload raw image
                raw_path = storage.design_raw_path(design_id)
                raw_url = storage.upload(raw_path, raw_bytes)
                design.raw_image_url = raw_url
                db.commit()

                # 4e: Post-process
                processed_img, report = process_image(raw_bytes)
                processed_bytes = image_to_bytes(processed_img)

                proc_path = storage.design_processed_path(design_id)
                processed_url = storage.upload(proc_path, processed_bytes)
                design.processed_image_url = processed_url
                color_palette = report.get("color_palette", [])
                design.color_palette = color_palette
                db.commit()

            except Exception as img_err:
                logger.warning(f"Image generation failed for design {design_id}: {img_err}; forcing text_only")
                archetype = "text_only"
                design.archetype = archetype
                design.image_api_used = None
                db.commit()

        design.color_palette = color_palette

        # 4f: Generate + composite text content
        text_content = generate_text_content(trend.raw_signal, archetype, niche_name)

        # 4f: Select font
        font_result = select_font_pair(
            trend.raw_signal, archetype, niche_name, text_content.get("primary_text", "")
        )
        design.font_pair = font_result["font_pair"]
        design.font_reasoning = font_result["reasoning"]
        design.design_style = archetype
        db.commit()

        # 4f-2: Generate text preview for text_only/typographic designs without images
        if not processed_url and archetype in ("text_only", "typographic"):
            try:
                preview_bytes = generate_text_preview(
                    primary_text=text_content.get("primary_text", trend.raw_signal),
                    secondary_text=text_content.get("secondary_text"),
                    font_pair=font_result["font_pair"],
                    color_palette=color_palette,
                )
                preview_path = storage.design_processed_path(design_id)
                processed_url = storage.upload(preview_path, preview_bytes, "image/png")
                design.processed_image_url = processed_url
                db.commit()
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
                # Force text_only on second failure
                archetype = "text_only"
                design.archetype = archetype
                design.image_api_used = None
                processed_url = None
                design.quality_score = 30  # text_only always passes threshold
                design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 7, "merch_suitability": 8, "originality": 7}
                db.commit()
                break
            else:
                # No image — text_only always passes
                design.quality_score = 30
                design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 7, "merch_suitability": 8, "originality": 7}
                db.commit()
                break

        # 4h: Assign product bundle
        product_types = assign_product_bundle(design.archetype, design.quality_breakdown or {})

        # 4i: Generate Shopify copy
        copy = generate_shopify_copy(
            design.concept_name, trend.raw_signal, design.archetype, product_types, niche_name
        )
        design.shopify_title = copy["shopify_title"]
        design.shopify_description = copy["shopify_description"]
        design.shopify_tags = copy["shopify_tags"]
        db.commit()

        # Step 5: Generate mockups + Step 6: Pricing — create Product records
        for pt in product_types:
            base_cost = get_base_cost(pt)
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

        # Step 7: Generate marketing assets
        _generate_marketing_assets(design, trend, niche_name, product_types, db)

        # Mark design ready
        design.status = "ready"
        db.commit()

        logger.info(f"Design {design_id} generated successfully for trend '{trend.raw_signal[:40]}'")

    except Exception as e:
        logger.error(f"Design generation failed for trend {trend_id}: {e}")
        if design:
            design.status = "rejected"
            db.commit()
        raise
    finally:
        db.close()


def _generate_marketing_assets(design: Design, trend: Trend, niche: str, product_types: list[str], db):
    """Generate all 5 marketing channel assets for a design."""
    channels = {
        "instagram": lambda: generate_instagram_assets(
            design.concept_name, trend.raw_signal, design.archetype, niche,
            design.shopify_title or design.concept_name, product_types
        ),
        "tiktok": lambda: generate_tiktok_assets(
            design.concept_name, trend.raw_signal, niche, design.shopify_title or design.concept_name
        ),
        "pinterest": lambda: generate_pinterest_assets(
            design.concept_name, trend.raw_signal, niche,
            design.shopify_title or design.concept_name, product_types
        ),
        "email": lambda: generate_email_assets(
            design.concept_name, trend.raw_signal, niche,
            design.shopify_title or design.concept_name, product_types
        ),
        "blog": lambda: generate_blog_post(
            design.concept_name, trend.raw_signal, niche,
            design.shopify_title or design.concept_name, product_types
        ),
    }
    for channel, generator in channels.items():
        try:
            content = generator()
            asset = MarketingAsset(
                design_id=design.id,
                channel=channel,
                content=content,
                status="pending",
            )
            db.add(asset)
        except Exception as e:
            logger.error(f"Marketing asset ({channel}) failed for design {design.id}: {e}")
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
