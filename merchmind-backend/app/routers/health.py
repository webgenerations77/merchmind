"""
Health check endpoints.
GET /health         — public, lightweight liveness check
GET /health/integrations — authenticated, runs all service health checks in parallel
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.routers.auth import verify_api_key

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict:
    """Public liveness probe. Returns 200 if the app is running."""
    return {"ok": True, "version": "1.0.0", "environment": settings.ENVIRONMENT}


@router.get("/health/integrations")
def health_integrations(_: str = Depends(verify_api_key)) -> dict:
    """
    Authenticated deep health check — hits every external service.
    Runs checks in parallel; returns within ~35s even if some services are slow.
    """
    checkers = {
        "printify": _check_printify,
        "shopify": _check_shopify,
        "instagram": _check_instagram,
        "tiktok": _check_tiktok,
        "pinterest": _check_pinterest,
        "klaviyo": _check_klaviyo,
        "google_trends": _check_google_trends,
        "reddit": _check_reddit,
        "twitter": _check_twitter,
        "image_generator": _check_image_generator,
        "placeit": _check_placeit,
    }

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn): name for name, fn in checkers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result(timeout=35)
            except Exception as e:
                results[name] = {"service": name, "ok": False, "error": str(e)}

    all_critical_ok = all(
        results.get(svc, {}).get("ok", False)
        for svc in ("printify", "shopify")
    )
    any_ok = any(r.get("ok") for r in results.values())

    return {
        "ok": all_critical_ok,
        "any_service_reachable": any_ok,
        "services": results,
    }


@router.post("/health/reset-data")
def reset_data(db: Session = Depends(get_db), _: str = Depends(verify_api_key)) -> dict:
    """Delete all pipeline data (products, designs, trends, batches, marketing assets, alerts). Keeps settings and niche clusters."""
    from app.models.product import Product
    from app.models.marketing_asset import MarketingAsset
    from app.models.design import Design
    from app.models.trend import Trend
    from app.models.batch import Batch
    from app.models.alert import Alert
    from app.models.feedback_log import FeedbackLog

    counts = {}
    for model, name in [
        (Product, "products"),
        (MarketingAsset, "marketing_assets"),
        (FeedbackLog, "feedback_logs"),
        (Design, "designs"),
        (Trend, "trends"),
        (Alert, "alerts"),
        (Batch, "batches"),
    ]:
        count = db.query(model).delete()
        counts[name] = count
    db.commit()
    logger.info("reset_data counts=%s", counts)
    return {"ok": True, "deleted": counts}


@router.get("/health/env-check")
def env_check(_: str = Depends(verify_api_key)) -> dict:
    """Check which env vars are set (masked values for debugging)."""
    import os
    keys = ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_BUCKET", "OPENAI_API_KEY", "REPLICATE_API_KEY", "ANTHROPIC_API_KEY"]
    result = {}
    for k in keys:
        val = os.environ.get(k, "")
        if val:
            result[k] = f"{val[:8]}...{val[-4:]}" if len(val) > 12 else f"{val[:4]}..."
        else:
            result[k] = "(not set)"
    return result


@router.post("/health/run-migration")
def run_migration(db: Session = Depends(get_db), _: str = Depends(verify_api_key)) -> dict:
    """Add flux_schnell to image_api enum if missing."""
    try:
        db.execute(
            __import__('sqlalchemy').text("ALTER TYPE image_api ADD VALUE IF NOT EXISTS 'flux_schnell'")
        )
        db.commit()
        return {"ok": True, "message": "flux_schnell added to image_api enum"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/health/purge-queue")
def purge_queue(_: str = Depends(verify_api_key)) -> dict:
    """Purge all pending Celery tasks from the Redis queue."""
    from app.tasks.celery_app import celery_app
    purged = celery_app.control.purge()
    return {"ok": True, "purged": purged}


@router.post("/health/test-image-gen")
def test_image_gen(_: str = Depends(verify_api_key)) -> dict:
    """Test image generation with a simple prompt and return detailed error if it fails."""
    prompt = "A simple red circle on a white background, flat design, bold outlines, centered composition"
    results = {}
    # Test DALL-E 3
    try:
        from app.services.design.image_generator import DALLe3Service
        dalle = DALLe3Service()
        img_bytes = dalle.generate(prompt)
        results["dalle3"] = {"ok": True, "bytes": len(img_bytes)}
    except Exception as e:
        results["dalle3"] = {"ok": False, "error": str(e), "type": type(e).__name__}

    # Test Flux Schnell
    try:
        from app.services.design.image_generator import FluxSchnellService
        flux = FluxSchnellService()
        img_bytes = flux.generate(prompt)
        results["flux_schnell"] = {"ok": True, "bytes": len(img_bytes)}
    except Exception as e:
        results["flux_schnell"] = {"ok": False, "error": str(e), "type": type(e).__name__}

    return {"ok": any(r["ok"] for r in results.values()), "results": results}


def _check_printify() -> dict:
    from app.services.publishing.printify_publisher import get_printify_service
    return get_printify_service().health_check()


def _check_shopify() -> dict:
    from app.services.publishing.shopify_publisher import get_shopify_service
    return get_shopify_service().health_check()


def _check_instagram() -> dict:
    from app.services.marketing.instagram_service import get_instagram_service
    return get_instagram_service().health_check()


def _check_tiktok() -> dict:
    from app.services.marketing.tiktok_service import get_tiktok_service
    return get_tiktok_service().health_check()


def _check_pinterest() -> dict:
    from app.services.marketing.pinterest_service import get_pinterest_service
    return get_pinterest_service().health_check()


def _check_klaviyo() -> dict:
    from app.services.marketing.klaviyo_service import get_klaviyo_service
    return get_klaviyo_service().health_check()


def _check_google_trends() -> dict:
    from app.services.intelligence.google_trends import get_google_trends_service
    return get_google_trends_service().health_check()


def _check_reddit() -> dict:
    from app.services.intelligence.reddit_scraper import get_reddit_scraper_service
    return get_reddit_scraper_service().health_check()


def _check_twitter() -> dict:
    from app.services.intelligence.twitter_scraper import get_twitter_scraper_service
    return get_twitter_scraper_service().health_check()


def _check_image_generator() -> dict:
    from app.services.design.image_generator import get_image_generator_service
    return get_image_generator_service().health_check()


def _check_placeit() -> dict:
    from app.services.design.placeit_service import get_placeit_service
    return get_placeit_service().health_check()
