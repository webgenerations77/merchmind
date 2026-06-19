"""
Monday 6am analytics sync task.
Pulls Shopify sales, Instagram/Pinterest insights, Klaviyo metrics,
flags underperformers, and decays trend scores.
"""
import logging
from datetime import datetime, timedelta, timezone, date as dt_date

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.product import Product
from app.models.sale import Sale
from app.models.alert import Alert
from app.models.design import Design
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_UNDERPERFORMER_DAYS = 14
_UNDERPERFORMER_SALE_THRESHOLD = 3
_TREND_DECAY_RATE = 0.05


@celery_app.task(name="tasks.analytics_sync")
def analytics_sync() -> dict:
    """
    Full analytics sync. Runs Monday at 06:00 UTC via Celery Beat.
    Returns summary dict for logging.
    """
    logger.info("analytics_sync.start")
    summary = {
        "shopify_orders": 0,
        "instagram_posts_synced": 0,
        "pinterest_pins_synced": 0,
        "underperformers_flagged": 0,
        "trend_scores_decayed": 0,
        "errors": [],
    }

    db = SessionLocal()
    try:
        summary["shopify_orders"] = _sync_shopify_sales(db)
        summary["instagram_posts_synced"] = _sync_instagram_insights(db)
        summary["pinterest_pins_synced"] = _sync_pinterest_insights(db)
        summary["underperformers_flagged"] = _check_underperformers(db)
        summary["trend_scores_decayed"] = _decay_trend_scores(db)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("analytics_sync.error error=%s", e)
        summary["errors"].append(str(e))
    finally:
        db.close()

    logger.info("analytics_sync.complete summary=%s", summary)
    return summary


def _sync_shopify_sales(db: Session) -> int:
    try:
        from app.services.publishing.shopify_publisher import get_shopify_service
        svc = get_shopify_service()
        since = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        orders = svc.get_sales_since(since)

        count = 0
        for order in orders:
            for item in order.get("line_items", []):
                shopify_product_id = str(item.get("product_id", ""))
                product = db.query(Product).filter(
                    Product.shopify_product_id == shopify_product_id
                ).first()
                if not product:
                    continue
                existing = db.query(Sale).filter(
                    Sale.shopify_order_id == str(order["id"]),
                    Sale.product_id == product.id,
                ).first()
                if existing:
                    continue
                price = float(item.get("price", 0))
                qty = int(item.get("quantity", 1))
                base_cost = float(product.printify_base_cost or 0)
                try:
                    sale_date = datetime.fromisoformat(
                        order.get("created_at", "").replace("Z", "+00:00")
                    ).date()
                except Exception:
                    sale_date = dt_date.today()
                sale = Sale(
                    product_id=product.id,
                    shopify_order_id=str(order["id"]),
                    quantity=qty,
                    gross_revenue=price,
                    printify_cost=base_cost,
                    net_profit=price - base_cost,
                    sale_date=sale_date,
                )
                db.add(sale)
                count += 1

        logger.info("analytics_sync.shopify orders=%d new_sales=%d", len(orders), count)
        return count
    except Exception as e:
        logger.error("analytics_sync.shopify failed error=%s", e)
        return 0


def _sync_instagram_insights(db: Session) -> int:
    try:
        from app.models.marketing_asset import MarketingAsset
        from app.services.marketing.instagram_service import get_instagram_service
        svc = get_instagram_service()

        assets = db.query(MarketingAsset).filter(
            MarketingAsset.channel == "instagram",
            MarketingAsset.status == "posted",
        ).all()

        count = 0
        for asset in assets:
            try:
                content = asset.content or {}
                media_id = content.get("media_id") or content.get("post_id", "")
                if not media_id:
                    continue
                metrics = svc.get_insights(media_id)
                if metrics:
                    asset.engagement = metrics
                    count += 1
            except Exception as e:
                logger.warning("analytics_sync.instagram_insight failed asset_id=%s error=%s", asset.id, e)

        logger.info("analytics_sync.instagram assets=%d synced=%d", len(assets), count)
        return count
    except Exception as e:
        logger.error("analytics_sync.instagram failed error=%s", e)
        return 0


def _sync_pinterest_insights(db: Session) -> int:
    try:
        from app.models.marketing_asset import MarketingAsset
        from app.services.marketing.pinterest_service import get_pinterest_service
        svc = get_pinterest_service()

        assets = db.query(MarketingAsset).filter(
            MarketingAsset.channel == "pinterest",
            MarketingAsset.status == "posted",
        ).all()

        today = datetime.now(tz=timezone.utc).date()
        week_ago = (today - timedelta(days=7)).isoformat()
        today_str = today.isoformat()

        count = 0
        for asset in assets:
            try:
                content = asset.content or {}
                pin_id = content.get("pin_id") or content.get("post_id", "")
                if not pin_id:
                    continue
                metrics = svc.get_pin_analytics(pin_id, week_ago, today_str)
                if metrics:
                    asset.engagement = metrics
                    count += 1
            except Exception as e:
                logger.warning("analytics_sync.pinterest_insight failed asset_id=%s error=%s", asset.id, e)

        logger.info("analytics_sync.pinterest assets=%d synced=%d", len(assets), count)
        return count
    except Exception as e:
        logger.error("analytics_sync.pinterest failed error=%s", e)
        return 0


def _check_underperformers(db: Session) -> int:
    try:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_UNDERPERFORMER_DAYS)
        products = db.query(Product).filter(
            Product.publish_status == "live",
            Product.created_at < cutoff,
        ).all()

        flagged = 0
        for product in products:
            sales_count = db.query(Sale).filter(
                Sale.product_id == product.id
            ).count()
            if sales_count < _UNDERPERFORMER_SALE_THRESHOLD:
                existing = db.query(Alert).filter(
                    Alert.product_id == product.id,
                    Alert.type == "underperformer",
                    Alert.resolved == False,
                ).first()
                if not existing:
                    alert = Alert(
                        product_id=product.id,
                        type="underperformer",
                        severity="warning",
                        message=f"Product has only {sales_count} sale(s) after {_UNDERPERFORMER_DAYS} days live.",
                        resolved=False,
                    )
                    db.add(alert)
                    flagged += 1

        logger.info("analytics_sync.underperformers products=%d flagged=%d", len(products), flagged)
        return flagged
    except Exception as e:
        logger.error("analytics_sync.underperformers failed error=%s", e)
        return 0


def _decay_trend_scores(db: Session) -> int:
    try:
        from app.models.trend import Trend
        trends = db.query(Trend).filter(Trend.final_score > 0).all()
        count = 0
        for trend in trends:
            trend.final_score = max(0, int(trend.final_score * (1 - _TREND_DECAY_RATE)))
            count += 1
        logger.info("analytics_sync.trend_decay decayed=%d", count)
        return count
    except Exception as e:
        logger.error("analytics_sync.trend_decay failed error=%s", e)
        return 0
