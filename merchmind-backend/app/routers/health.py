"""
Health check endpoints.
GET /health         — public, lightweight liveness check
GET /health/integrations — authenticated, runs all service health checks in parallel
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends

from app.config import settings
from app.routers.auth import verify_api_key

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict:
    """Public liveness probe. Returns 200 if the app is running."""
    return {"ok": True, "version": "1.0.0", "environment": settings.ENVIRONMENT}


@router.get("/health/api-balance")
def api_balance(_: str = Depends(verify_api_key)) -> dict:
    """Check API credit balances for Claude, OpenAI, and Replicate."""
    from app.services.api_balance import check_all_balances
    return check_all_balances()


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
