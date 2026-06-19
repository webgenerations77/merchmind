"""
Niche cluster management endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.niche_cluster import NicheCluster
from app.schemas.niche_cluster import NicheClusterOut, NicheClusterCreate, NicheClusterUpdate
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/niche-clusters", tags=["niche_clusters"])


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_clusters(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    clusters = db.query(NicheCluster).order_by(NicheCluster.created_at.asc()).all()
    return _envelope([NicheClusterOut.model_validate(c).model_dump() for c in clusters])


@router.patch("/{cluster_id}")
def update_cluster(
    cluster_id: UUID,
    body: NicheClusterUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    cluster = db.query(NicheCluster).filter(NicheCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(404, f"Cluster {cluster_id} not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cluster, field, value)
    db.commit()
    return _envelope(NicheClusterOut.model_validate(cluster).model_dump())


@router.post("")
def create_cluster(
    body: NicheClusterCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    cluster = NicheCluster(**body.model_dump())
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return _envelope(NicheClusterOut.model_validate(cluster).model_dump())
