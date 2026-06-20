"""
Collection CRUD + generate endpoint.
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.collection import Collection
from app.models.design import Design
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionOut, CollectionWithDesigns
from app.routers.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/collections", tags=["collections"])


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_collections(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    rows = db.query(Collection).order_by(Collection.created_at.desc()).all()
    result = []
    for c in rows:
        out = CollectionOut.model_validate(c).model_dump()
        out["design_count"] = db.query(Design).filter(Design.collection_id == c.id, Design.is_deleted == False).count()
        result.append(out)
    return _envelope(result)


@router.get("/{collection_id}")
def get_collection(collection_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(404, "Collection not found")
    designs = db.query(Design).filter(
        Design.collection_id == c.id, Design.is_deleted == False
    ).order_by(Design.created_at).all()
    out = CollectionOut.model_validate(c).model_dump()
    out["design_count"] = len(designs)
    out["designs"] = [
        {
            "id": str(d.id),
            "concept_name": d.concept_name,
            "archetype": d.archetype,
            "processed_image_url": d.processed_image_url,
            "quality_score": d.quality_score,
            "status": d.status,
        }
        for d in designs
    ]
    return _envelope(out)


@router.post("")
def create_collection(body: CollectionCreate, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    c = Collection(
        name=body.name,
        description=body.description,
        style_guide=body.style_guide,
        max_designs=body.max_designs,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _envelope(CollectionOut.model_validate(c).model_dump())


@router.patch("/{collection_id}")
def update_collection(
    collection_id: UUID,
    body: CollectionUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(404, "Collection not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.utcnow()
    db.commit()
    return _envelope(CollectionOut.model_validate(c).model_dump())


@router.delete("/{collection_id}")
def delete_collection(collection_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(404, "Collection not found")
    db.query(Design).filter(Design.collection_id == c.id).update({"collection_id": None})
    db.delete(c)
    db.commit()
    return _envelope({"deleted": True})


@router.post("/{collection_id}/generate")
def generate_collection_designs(
    collection_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Generate designs for a collection using its style guide."""
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(404, "Collection not found")
    if c.status == "generating":
        raise HTTPException(409, "Collection is already generating")

    existing = db.query(Design).filter(Design.collection_id == c.id, Design.is_deleted == False).count()
    remaining = max(0, c.max_designs - existing)
    if remaining == 0:
        raise HTTPException(400, f"Collection already has {existing} designs (max {c.max_designs})")

    c.status = "generating"
    c.updated_at = datetime.utcnow()
    db.commit()

    from app.tasks.collection_generator import generate_collection_task
    generate_collection_task.delay(str(collection_id), remaining)

    return _envelope({"collection_id": str(c.id), "generating": remaining})
