"""
Monday 9am publish task.
Publishes all approved designs to Printify + Shopify in order.
"""
import logging
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.design import Design
from app.models.product import Product
from app.models.marketing_asset import MarketingAsset
from app.models.alert import Alert
from app.services.publishing.printify_publisher import create_product, delete_product, generate_mockups
from app.services.publishing.shopify_publisher import create_product_draft, activate_product

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    name="app.tasks.publish_queue.publish_approved_products",
)
def publish_approved_products(self):
    """
    Publish all approved designs in queue order.
    Runs Monday at 9am. Each design is atomic — failure does not block others.
    """
    db = SessionLocal()
    try:
        approved_designs = (
            db.query(Design)
            .filter(Design.status == "approved", Design.is_deleted == False)
            .order_by(Design.approved_at.asc())
            .all()
        )
        logger.info(f"Publishing {len(approved_designs)} approved designs")

        for design in approved_designs:
            _publish_single_design(design, db)

        logger.info("Publish queue complete")
    except Exception as e:
        logger.exception(f"Publish queue task crashed: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()


def _publish_single_design(design: Design, db):
    """Publish one design: Printify → Shopify → activate → schedule marketing."""
    products = (
        db.query(Product)
        .filter(Product.design_id == design.id, Product.publish_status == "pending")
        .all()
    )

    all_mockup_urls = []
    printify_ids = []
    publish_failed = False

    for product in products:
        # Step 1: Create Printify product
        printify_id = None
        try:
            image_url = design.processed_image_url or design.raw_image_url or ""
            product_label = product.product_type.replace("_", " ").title()
            base_name = design.concept_name or design.shopify_title or "Design"
            printify_id = create_product(
                product_type=product.product_type,
                title=f"{base_name} — {product_label}",
                description=design.shopify_description or "",
                image_url=image_url,
                retail_price=float(product.retail_price),
            )
            product.printify_product_id = printify_id
            product.publish_status = "printify_only"
            db.commit()
            printify_ids.append(printify_id)

            # Fetch mockups
            mockups = generate_mockups(printify_id)
            product.mockup_urls = mockups
            if mockups.get("front"):
                all_mockup_urls.append(mockups["front"])
            db.commit()

        except Exception as e:
            logger.error(f"Printify failed for product {product.id} ({product.product_type}): {e}")
            product.publish_status = "failed"
            db.commit()
            _fire_alert(db, "publish_failed", "critical", design_id=design.id,
                        message=f"Printify publish failed for {product.product_type}: {e}")
            publish_failed = True
            continue

        # Step 2: Create Shopify draft
        shopify_id = None
        try:
            shopify_id = create_product_draft(
                title=design.shopify_title or design.concept_name,
                description=design.shopify_description or "",
                tags=design.shopify_tags or [],
                price=float(product.retail_price),
                image_urls=all_mockup_urls,
            )
            product.shopify_product_id = shopify_id
            db.commit()

        except Exception as e:
            logger.error(f"Shopify draft failed for product {product.id}: {e}")
            # Rollback Printify product
            if printify_id:
                delete_product(printify_id)
                product.printify_product_id = None
                product.publish_status = "failed"
                db.commit()
            _fire_alert(db, "publish_failed", "critical", design_id=design.id,
                        message=f"Shopify draft failed for {product.product_type}: {e}")
            publish_failed = True
            continue

        # Step 3: Activate Shopify product
        try:
            activate_product(shopify_id)
            product.publish_status = "live"
            product.published_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.error(f"Shopify activate failed for product {product.id}: {e}")
            product.publish_status = "failed"
            db.commit()
            _fire_alert(db, "publish_failed", "warning", design_id=design.id,
                        message=f"Shopify activate failed for {product.product_type}: {e}")

    # Step 4: Schedule approved marketing assets
    if not publish_failed:
        _schedule_marketing(design, db)


def _schedule_marketing(design: Design, db):
    """Mark approved marketing assets as scheduled."""
    assets = (
        db.query(MarketingAsset)
        .filter(
            MarketingAsset.design_id == design.id,
            MarketingAsset.status == "approved",
        )
        .all()
    )
    for asset in assets:
        # Use pre-calculated send time from content if available
        send_time_str = asset.content.get("send_time_recommendation", "")
        if send_time_str:
            try:
                asset.scheduled_for = datetime.fromisoformat(send_time_str.rstrip("Z"))
            except ValueError:
                pass
        asset.status = "scheduled"
    db.commit()


def _fire_alert(db, alert_type, severity, design_id=None, message=""):
    alert = Alert(
        type=alert_type,
        severity=severity,
        design_id=design_id,
        message=message,
    )
    db.add(alert)
    db.commit()
