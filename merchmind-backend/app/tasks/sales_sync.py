"""
Weekly Shopify sales sync task (Monday 6am).
Syncs orders from the past 7 days into the sales table.
"""
import logging
from datetime import datetime, timedelta, date
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.sale import Sale
from app.models.product import Product
from app.services.publishing.shopify_publisher import get_sales_since

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    name="app.tasks.sales_sync.sync_shopify_sales",
)
def sync_shopify_sales(self, since_days: int = 7):
    """
    Sync Shopify sales data into local database.
    Fetches orders from the past `since_days` days.
    """
    db = SessionLocal()
    try:
        since_date = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"Syncing Shopify sales since {since_date}")

        orders = get_sales_since(since_date)
        synced = 0
        skipped = 0

        for order in orders:
            for line_item in order.get("line_items", []):
                shopify_order_id = str(order.get("id", ""))
                shopify_product_id = str(line_item.get("product_id", ""))

                # Find matching product record
                product = (
                    db.query(Product)
                    .filter(Product.shopify_product_id == shopify_product_id)
                    .first()
                )
                if not product:
                    skipped += 1
                    continue

                # Check for duplicate
                existing = (
                    db.query(Sale)
                    .filter(
                        Sale.shopify_order_id == shopify_order_id,
                        Sale.product_id == product.id,
                    )
                    .first()
                )
                if existing:
                    skipped += 1
                    continue

                quantity = int(line_item.get("quantity", 1))
                price = float(line_item.get("price", 0))
                gross_revenue = price * quantity
                printify_cost = float(product.printify_base_cost) * quantity
                net_profit = gross_revenue - printify_cost

                sale_date_str = order.get("created_at", "")[:10]
                try:
                    sale_date = date.fromisoformat(sale_date_str)
                except ValueError:
                    sale_date = date.today()

                sale = Sale(
                    product_id=product.id,
                    shopify_order_id=shopify_order_id,
                    quantity=quantity,
                    gross_revenue=gross_revenue,
                    printify_cost=printify_cost,
                    net_profit=net_profit,
                    sale_date=sale_date,
                    variant=line_item.get("variant_title", ""),
                )
                db.add(sale)
                synced += 1

        db.commit()
        logger.info(f"Sales sync complete: {synced} synced, {skipped} skipped/duplicate")

    except Exception as e:
        logger.exception(f"Sales sync failed: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()
