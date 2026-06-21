"""
Every-6h health monitor Celery task.
Checks all critical and non-critical services in parallel.
Creates Alert records for critical failures (Anthropic, Printify, Shopify).
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_CRITICAL_SERVICES = {"anthropic", "printify"}


@celery_app.task(name="tasks.health_monitor")
def health_monitor() -> dict:
    """Run parallel health checks across all services. Creates alerts for critical failures."""
    logger.info("health_monitor.start")
    results = _run_all_checks()
    _process_results(results)
    logger.info("health_monitor.complete results=%s", {k: v.get("ok") for k, v in results.items()})
    return results


def _run_all_checks() -> dict[str, dict]:
    checkers = {
        "anthropic": _check_anthropic,
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

    return results


def _process_results(results: dict[str, dict]) -> None:
    """Create Alert records for critical services that are down."""
    from app.database import SessionLocal
    from app.models.alert import Alert

    db = SessionLocal()
    try:
        for service_name, result in results.items():
            if service_name not in _CRITICAL_SERVICES:
                continue
            if result.get("ok"):
                continue

            existing = db.query(Alert).filter(
                Alert.type == "api_down",
                Alert.resolved == False,
                Alert.message.like(f"%{service_name}%"),
            ).first()
            if existing:
                continue

            error_detail = result.get("error", "unknown error")
            alert = Alert(
                type="api_down",
                severity="critical",
                message=f"CRITICAL: {service_name} health check failed — {error_detail}",
                resolved=False,
            )
            db.add(alert)
            logger.error("health_monitor.critical_alert service=%s error=%s", service_name, error_detail)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("health_monitor.alert_creation failed error=%s", e)
    finally:
        db.close()


def _check_anthropic() -> dict:
    try:
        from app.utils.claude_client import claude
        text, _ = claude.haiku("health_check", [{"role": "user", "content": "Reply with just OK"}], max_tokens=5)
        return {"service": "anthropic", "ok": True}
    except Exception as e:
        return {"service": "anthropic", "ok": False, "error": str(e)}


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
    from app.services.design.dynamic_mockups import get_dynamic_mockups_service
    return get_dynamic_mockups_service().health_check()
