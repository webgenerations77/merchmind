"""
App settings endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.settings import AppSettings
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/settings", tags=["settings"])


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def get_settings(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    settings = db.query(AppSettings).first()
    if not settings:
        raise HTTPException(404, "Settings not found — run seed script first")
    return _envelope(SettingsOut.model_validate(settings).model_dump())


@router.patch("")
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    settings = db.query(AppSettings).first()
    if not settings:
        raise HTTPException(404, "Settings not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.utcnow()
    db.commit()
    return _envelope(SettingsOut.model_validate(settings).model_dump())
