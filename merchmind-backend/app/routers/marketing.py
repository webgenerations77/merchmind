"""
Marketing asset management endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.marketing_asset import MarketingAsset
from app.schemas.marketing_asset import MarketingAssetOut, MarketingAssetUpdate
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("/{design_id}")
def get_design_assets(design_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    assets = db.query(MarketingAsset).filter(MarketingAsset.design_id == design_id).all()
    return _envelope([MarketingAssetOut.model_validate(a).model_dump() for a in assets])


@router.patch("/{asset_id}/approve")
def approve_asset(asset_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    asset = db.query(MarketingAsset).filter(MarketingAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    asset.status = "approved"
    db.commit()
    return _envelope({"id": str(asset_id), "status": "approved"})


@router.patch("/{asset_id}/disable")
def disable_asset(asset_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    asset = db.query(MarketingAsset).filter(MarketingAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    asset.status = "failed"
    db.commit()
    return _envelope({"id": str(asset_id), "status": "disabled"})


@router.patch("/{asset_id}/content")
def update_asset_content(
    asset_id: UUID,
    body: MarketingAssetUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    asset = db.query(MarketingAsset).filter(MarketingAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    return _envelope(MarketingAssetOut.model_validate(asset).model_dump())
