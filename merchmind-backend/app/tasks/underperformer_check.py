"""
Underperformer check task (Monday 7am).
Flags products with zero sales after N weeks.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.product import Product
from app.models.sale import Sale
from app.models.alert import Alert
from app.models.settings import AppSettings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    name="app.tasks.underperformer_check.check_underperformers",
)
def check_underperformers(self):
    """
    Find products that have been live for N weeks with zero sales.
    Creates underperformer alerts and fires push notification.
    """
    db = SessionLocal()
    try:
        settings_row = db.query(AppSettings).first()
        underperform_weeks = settings_row.underperform_weeks if settings_row else 4
        cutoff_date = datetime.utcnow() - timedelta(weeks=underperform_weeks)

        # Products live for longer than threshold with no sales
        live_products = (
            db.query(Product)
            .filter(
                Product.publish_status == "live",
                Product.published_at <= cutoff_date,
            )
            .all()
        )

        underperformers = []
        for product in live_products:
            sale_count = db.query(func.count(Sale.id)).filter(Sale.product_id == product.id).scalar()
            if sale_count == 0:
                underperformers.append(product)

        logger.info(f"Found {len(underperformers)} underperforming products")

        for product in underperformers:
            # Check if alert already exists for this product
            existing_alert = (
                db.query(Alert)
                .filter(
                    Alert.product_id == product.id,
                    Alert.type == "underperformer",
                    Alert.resolved == False,
                )
                .first()
            )
            if existing_alert:
                continue

            weeks_live = (datetime.utcnow() - product.published_at).days // 7
            alert = Alert(
                type="underperformer",
                severity="warning",
                product_id=product.id,
                message=(
                    f"Product has been live {weeks_live} weeks with 0 sales. "
                    f"Consider unpublishing or repricing."
                ),
                action_url=f"/products/{product.id}",
            )
            db.add(alert)

        db.commit()

        if underperformers:
            from app.services.notifications.push_notifications import notify_alert
            notify_alert(
                "underperformer",
                f"{len(underperformers)} products have 0 sales after {underperform_weeks} weeks",
                "underperformer",
            )

    except Exception as e:
        logger.exception(f"Underperformer check failed: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()
