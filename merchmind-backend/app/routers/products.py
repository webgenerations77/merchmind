"""
Product management endpoints.
"""
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.alert import Alert
from app.schemas.product import ProductOut, ProductUpdate
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_products(
    status: str = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    query = db.query(Product)
    if status:
        query = query.filter(Product.publish_status == status)
    products = query.order_by(Product.created_at.desc()).limit(200).all()
    return _envelope([ProductOut.model_validate(p).model_dump() for p in products])


@router.get("/{product_id}")
def get_product(product_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, f"Product {product_id} not found")
    return _envelope(ProductOut.model_validate(product).model_dump())


@router.patch("/{product_id}")
def update_product(
    product_id: UUID,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, f"Product {product_id} not found")
    if body.retail_price is not None:
        product.retail_price = body.retail_price
    if body.publish_status is not None:
        product.publish_status = body.publish_status
    db.commit()
    return _envelope(ProductOut.model_validate(product).model_dump())


@router.post("/{product_id}/unpublish")
def unpublish_product(product_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Emergency unpublish: set Shopify product to draft."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, f"Product {product_id} not found")

    try:
        from app.services.publishing.shopify_publisher import unpublish_product as shopify_unpublish
        if product.shopify_product_id:
            shopify_unpublish(product.shopify_product_id)
        product.publish_status = "unpublished"
        product.unpublished_at = datetime.utcnow()
        db.commit()
        return _envelope({"id": str(product_id), "status": "unpublished"})
    except Exception as e:
        logger.error(f"Unpublish failed for product {product_id}: {e}")
        raise HTTPException(500, f"Unpublish failed: {e}")


@router.post("/{product_id}/retry-publish")
def retry_publish(product_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Retry a failed publish."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, f"Product {product_id} not found")
    if product.publish_status != "failed":
        raise HTTPException(400, f"Product {product_id} is not in failed state")

    product.publish_status = "pending"
    db.commit()

    from app.tasks.publish_queue import publish_approved_products
    task = publish_approved_products.delay()
    return _envelope({"task_id": task.id, "message": "Retry publish queued"})
