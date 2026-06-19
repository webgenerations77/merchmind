"""
Alert management endpoints.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertOut
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_alerts(
    resolved: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    query = db.query(Alert)
    if resolved is not None:
        query = query.filter(Alert.resolved == resolved)
    if severity:
        query = query.filter(Alert.severity == severity)
    alerts = query.order_by(Alert.created_at.desc()).limit(100).all()
    return _envelope([AlertOut.model_validate(a).model_dump() for a in alerts])


@router.patch("/{alert_id}/resolve")
def resolve_alert(alert_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, f"Alert {alert_id} not found")
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return _envelope({"id": str(alert_id), "resolved": True})
