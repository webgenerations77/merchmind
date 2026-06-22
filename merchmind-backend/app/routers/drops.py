"""
Merch Drops — schedule coordinated product launches.
"""
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.merch_drop import MerchDrop
from app.models.product import Product
from app.models.design import Design
from app.schemas.merch_drop import MerchDropCreate, MerchDropUpdate, MerchDropOut, MerchDropDetail
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/drops", tags=["drops"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


def _drop_to_detail(drop: MerchDrop) -> dict:
    products = drop.products or []
    data = MerchDropOut.model_validate(drop).model_dump()
    data["product_count"] = len(products)
    data["products"] = []
    for p in products:
        design = p.design
        data["products"].append({
            "id": str(p.id),
            "design_id": str(p.design_id),
            "product_type": p.product_type,
            "publish_status": p.publish_status,
            "retail_price": float(p.retail_price),
            "mockup_urls": p.mockup_urls or {},
            "concept_name": design.concept_name if design else "",
            "processed_image_url": design.processed_image_url if design else None,
        })
    return data


@router.get("")
def list_drops(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drops = (
        db.query(MerchDrop)
        .options(joinedload(MerchDrop.products))
        .order_by(MerchDrop.scheduled_at.desc())
        .all()
    )
    result = []
    for drop in drops:
        d = MerchDropOut.model_validate(drop).model_dump()
        d["product_count"] = len(drop.products or [])
        result.append(d)
    return _envelope(result)


@router.get("/upcoming")
def list_upcoming_drops(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drops = (
        db.query(MerchDrop)
        .options(joinedload(MerchDrop.products))
        .filter(MerchDrop.status == "scheduled")
        .order_by(MerchDrop.scheduled_at.asc())
        .all()
    )
    result = []
    for drop in drops:
        d = MerchDropOut.model_validate(drop).model_dump()
        d["product_count"] = len(drop.products or [])
        result.append(d)
    return _envelope(result)


@router.get("/{drop_id}")
def get_drop(drop_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drop = (
        db.query(MerchDrop)
        .options(
            joinedload(MerchDrop.products).joinedload(Product.design),
        )
        .filter(MerchDrop.id == drop_id)
        .first()
    )
    if not drop:
        raise HTTPException(404, "Drop not found")
    return _envelope(_drop_to_detail(drop))


@router.post("")
def create_drop(body: MerchDropCreate, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drop = MerchDrop(name=body.name, scheduled_at=body.scheduled_at)
    db.add(drop)
    db.commit()
    db.refresh(drop)
    d = MerchDropOut.model_validate(drop).model_dump()
    d["product_count"] = 0
    return _envelope(d)


@router.patch("/{drop_id}")
def update_drop(drop_id: UUID, body: MerchDropUpdate, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drop = db.query(MerchDrop).filter(MerchDrop.id == drop_id).first()
    if not drop:
        raise HTTPException(404, "Drop not found")
    if drop.status != "scheduled":
        raise HTTPException(409, "Only scheduled drops can be edited")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(drop, field, value)
    drop.updated_at = datetime.utcnow()
    db.commit()
    d = MerchDropOut.model_validate(drop).model_dump()
    d["product_count"] = len(drop.products or [])
    return _envelope(d)


@router.delete("/{drop_id}")
def delete_drop(drop_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    drop = (
        db.query(MerchDrop)
        .options(joinedload(MerchDrop.products))
        .filter(MerchDrop.id == drop_id)
        .first()
    )
    if not drop:
        raise HTTPException(404, "Drop not found")
    if drop.status not in ("scheduled", "failed"):
        raise HTTPException(409, "Only scheduled or failed drops can be deleted")
    for product in (drop.products or []):
        product.drop_id = None
    db.delete(drop)
    db.commit()
    return _envelope({"deleted": True})


@router.post("/{drop_id}/publish")
def publish_drop_now(drop_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Manually fire a drop immediately, regardless of scheduled time."""
    drop = db.query(MerchDrop).filter(MerchDrop.id == drop_id).first()
    if not drop:
        raise HTTPException(404, "Drop not found")
    if drop.status not in ("scheduled", "failed"):
        raise HTTPException(409, f"Drop is already {drop.status}")

    from app.tasks.drop_publisher import execute_drop
    execute_drop.delay(str(drop_id))
    return _envelope({"id": str(drop_id), "status": "publishing"})


@router.post("/{drop_id}/remove-product/{product_id}")
def remove_product_from_drop(
    drop_id: UUID,
    product_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Remove a product from a drop and revert it to pending status."""
    drop = db.query(MerchDrop).filter(MerchDrop.id == drop_id).first()
    if not drop:
        raise HTTPException(404, "Drop not found")
    if drop.status != "scheduled":
        raise HTTPException(409, "Products can only be removed from scheduled drops")
    product = db.query(Product).filter(Product.id == product_id, Product.drop_id == drop_id).first()
    if not product:
        raise HTTPException(404, "Product not in this drop")
    product.drop_id = None
    product.publish_status = "pending"
    db.commit()
    return _envelope({"removed": True, "product_id": str(product_id)})


@router.post("/schedule-design/{design_id}")
def schedule_design_for_drop(
    design_id: UUID,
    drop_id: UUID | None = None,
    drop_name: str | None = None,
    scheduled_at: datetime | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Schedule a design for a merch drop. Either assign to an existing drop (drop_id)
    or create a new one (drop_name + scheduled_at).

    This publishes products to Printify immediately but keeps Shopify listings as drafts.
    Products go live when the drop fires.
    """
    design = (
        db.query(Design)
        .options(joinedload(Design.products))
        .filter(Design.id == design_id, Design.is_deleted == False)
        .first()
    )
    if not design:
        raise HTTPException(404, f"Design {design_id} not found")

    if drop_id:
        drop = db.query(MerchDrop).filter(MerchDrop.id == drop_id, MerchDrop.status == "scheduled").first()
        if not drop:
            raise HTTPException(404, "Drop not found or not in scheduled status")
    elif drop_name and scheduled_at:
        drop = MerchDrop(name=drop_name, scheduled_at=scheduled_at)
        db.add(drop)
        db.flush()
    else:
        raise HTTPException(400, "Provide either drop_id or both drop_name and scheduled_at")

    design.status = "approved"
    design.approved_at = datetime.utcnow()

    from app.services.publishing.printify_publisher import _get as _get_printify
    svc = _get_printify()

    published = []
    failed = []
    for product in design.products:
        product.drop_id = drop.id
        if product.printify_product_id:
            try:
                svc.publish_product(product.printify_product_id)
                product.publish_status = "printify_only"
                product.published_at = datetime.utcnow()
                published.append(product.product_type)
            except Exception as e:
                product.publish_status = "failed"
                failed.append({"type": product.product_type, "error": str(e)})
                logger.warning("Printify publish failed for %s: %s", product.product_type, e)
        else:
            product.publish_status = "printify_only"
            published.append(product.product_type)

    db.commit()

    return _envelope({
        "design_id": str(design_id),
        "drop_id": str(drop.id),
        "drop_name": drop.name,
        "status": "scheduled",
        "published_to_printify": published,
        "failed": failed,
    })
