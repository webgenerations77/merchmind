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
from app.models.design import Design
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
    include_retired: bool = False,
    search: str = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    query = db.query(Product).join(Design, Product.design_id == Design.id, isouter=True)
    if status:
        query = query.filter(Product.publish_status == status)
    elif not include_retired:
        query = query.filter(Product.publish_status != "retired")
    if search:
        query = query.filter(Design.concept_name.ilike(f"%{search}%"))
    products = query.order_by(Product.created_at.desc()).limit(200).all()
    results = []
    for p in products:
        out = ProductOut.model_validate(p).model_dump()
        if p.design:
            out["concept_name"] = p.design.concept_name
            out["batch_id"] = str(p.design.batch_id) if p.design.batch_id else None
            out["processed_image_url"] = p.design.processed_image_url
            mockups = out.get("mockup_urls") or {}
            out["primary_mockup_url"] = mockups.get("front") or mockups.get(next(iter(mockups), ""), None) if mockups else None
        results.append(out)
    return _envelope(results)


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
    if body.target_store is not None:
        product.target_store = body.target_store
    if body.selected_color is not None:
        product.selected_color = body.selected_color
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
