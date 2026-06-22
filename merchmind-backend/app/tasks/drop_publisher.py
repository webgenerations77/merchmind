"""
Celery tasks for scheduled merch drop execution.

When a drop fires:
1. Set status to in_progress
2. Publish each product's Shopify listing (Printify publish call makes it live)
3. Optionally generate marketing assets if marketing is enabled
4. Set status to published (or failed if any product failed)
"""
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    name="app.tasks.drop_publisher.execute_drop",
)
def execute_drop(self, drop_id: str):
    from app.database import SessionLocal
    from app.models.merch_drop import MerchDrop
    from app.models.product import Product
    from app.models.settings import AppSettings
    from app.models.drop_marketing_asset import DropMarketingAsset
    from sqlalchemy.orm import joinedload
    import app.models  # noqa: F401

    db = SessionLocal()
    try:
        drop = (
            db.query(MerchDrop)
            .options(joinedload(MerchDrop.products).joinedload(Product.design))
            .filter(MerchDrop.id == drop_id)
            .first()
        )
        if not drop:
            logger.error("Drop %s not found", drop_id)
            return

        if drop.status not in ("scheduled", "failed"):
            logger.info("Drop %s already %s, skipping", drop_id, drop.status)
            return

        drop.status = "in_progress"
        db.commit()
        logger.info("Drop %s (%s) firing with %d products", drop_id, drop.name, len(drop.products))

        from app.services.publishing.printify_publisher import _get as _get_printify
        svc = _get_printify()

        published = []
        failed = []
        for product in drop.products:
            if product.publish_status == "live":
                published.append(product)
                continue
            if product.printify_product_id:
                try:
                    svc.publish_product(product.printify_product_id)
                    product.publish_status = "live"
                    product.published_at = datetime.now(timezone.utc)
                    published.append(product)
                    logger.info("Drop %s: published %s (%s)", drop_id, product.product_type, product.id)
                except Exception as e:
                    product.publish_status = "failed"
                    failed.append({"product_id": str(product.id), "type": product.product_type, "error": str(e)})
                    logger.error("Drop %s: failed to publish %s: %s", drop_id, product.product_type, e)
            else:
                product.publish_status = "failed"
                failed.append({"product_id": str(product.id), "type": product.product_type, "error": "No printify_product_id"})
        db.commit()

        settings_row = db.query(AppSettings).first()
        marketing_enabled = settings_row.marketing_generation_enabled if settings_row else False

        if marketing_enabled and published:
            _generate_drop_marketing(drop, published, db)
        elif not marketing_enabled:
            logger.info("Marketing paused — skipping drop marketing for %s", drop_id)

        if failed and not published:
            drop.status = "failed"
        else:
            drop.status = "published"
        drop.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Drop %s complete: %d published, %d failed",
            drop_id, len(published), len(failed),
        )

    except Exception as e:
        logger.exception("Drop %s execution failed: %s", drop_id, e)
        try:
            drop = db.query(MerchDrop).filter(MerchDrop.id == drop_id).first()
            if drop:
                drop.status = "failed"
                drop.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=e)
    finally:
        db.close()


def _generate_drop_marketing(drop, published_products, db):
    """Generate marketing assets for the drop — per-product assets plus a drop announcement."""
    from app.models.drop_marketing_asset import DropMarketingAsset
    from app.services.marketing.combined_generator import generate_all_marketing_assets

    for product in published_products:
        design = product.design
        if not design:
            continue
        try:
            all_content = generate_all_marketing_assets(
                design.concept_name,
                "",
                design.archetype,
                "",
                design.shopify_title or design.concept_name,
                [product.product_type],
            )
            for channel, content in all_content.items():
                asset = DropMarketingAsset(
                    drop_id=drop.id,
                    channel=channel,
                    content=content,
                    status="pending",
                )
                db.add(asset)
        except Exception as e:
            logger.error("Marketing generation failed for product %s in drop %s: %s", product.id, drop.id, e)

    try:
        product_names = [p.design.shopify_title or p.design.concept_name for p in published_products if p.design]
        product_types = list({p.product_type for p in published_products})
        _generate_drop_announcement(drop, product_names, product_types, db)
    except Exception as e:
        logger.error("Drop announcement generation failed for %s: %s", drop.id, e)

    db.commit()


def _generate_drop_announcement(drop, product_names, product_types, db):
    """Generate a single 'drop announcement' marketing post for all channels."""
    from app.models.drop_marketing_asset import DropMarketingAsset
    from app.utils.claude_client import claude

    products_list = "\n".join(f"- {name}" for name in product_names[:10])
    types_str = ", ".join(product_types)

    prompt = (
        f"Write a social media drop announcement for the \"{drop.name}\" merch drop.\n"
        f"Products in this drop ({len(product_names)} designs, available as {types_str}):\n"
        f"{products_list}\n\n"
        f"Write ONE announcement post for Instagram/social media. Keep it under 200 words.\n"
        f"Include:\n"
        f"- Excitement about the new drop\n"
        f"- Mention it's a coordinated collection launch\n"
        f"- Call to action to shop now\n"
        f"- Relevant hashtags\n\n"
        f"Reply with ONLY the post text, no preamble."
    )

    text, _ = claude.haiku(
        "drop_announcement",
        [{"role": "user", "content": prompt}],
        max_tokens=512,
    )

    asset = DropMarketingAsset(
        drop_id=drop.id,
        channel="instagram",
        content={
            "type": "drop_announcement",
            "caption": text,
            "product_count": len(product_names),
            "drop_name": drop.name,
        },
        status="pending",
    )
    db.add(asset)


@celery_app.task(name="app.tasks.drop_publisher.check_scheduled_drops")
def check_scheduled_drops():
    """Periodic task: find drops whose scheduled_at has passed and fire them."""
    from app.database import SessionLocal
    from app.models.merch_drop import MerchDrop
    import app.models  # noqa: F401

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_drops = db.query(MerchDrop).filter(
            MerchDrop.status == "scheduled",
            MerchDrop.scheduled_at <= now,
        ).all()

        for drop in due_drops:
            logger.info("Firing scheduled drop %s (%s)", drop.id, drop.name)
            execute_drop.delay(str(drop.id))

        if due_drops:
            logger.info("Queued %d drops for execution", len(due_drops))
    except Exception as e:
        logger.exception("check_scheduled_drops failed: %s", e)
    finally:
        db.close()
