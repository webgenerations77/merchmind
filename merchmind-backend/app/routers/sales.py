"""
Sales data and analytics endpoints.
"""
import logging
from uuid import UUID
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.sale import Sale
from app.models.product import Product
from app.schemas.sale import SaleOut, SalesAnalytics
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/sales", tags=["sales"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_sales(
    product_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    query = db.query(Sale)
    if product_id:
        query = query.filter(Sale.product_id == product_id)
    if from_date:
        query = query.filter(Sale.sale_date >= from_date)
    if to_date:
        query = query.filter(Sale.sale_date <= to_date)
    sales = query.order_by(Sale.sale_date.desc()).limit(limit).all()
    return _envelope([SaleOut.model_validate(s).model_dump() for s in sales])


@router.get("/by-product/{product_id}")
def get_sales_by_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    sales = db.query(Sale).filter(Sale.product_id == product_id).order_by(Sale.sale_date.desc()).all()
    return _envelope([SaleOut.model_validate(s).model_dump() for s in sales])


@router.get("/analytics")
def get_sales_analytics(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Aggregated sales analytics."""
    totals = db.query(
        func.sum(Sale.gross_revenue).label("total_revenue"),
        func.sum(Sale.net_profit).label("total_profit"),
        func.count(Sale.id).label("total_orders"),
    ).first()

    # Best seller by revenue
    best_seller = (
        db.query(Sale.product_id, func.sum(Sale.gross_revenue).label("rev"))
        .group_by(Sale.product_id)
        .order_by(func.sum(Sale.gross_revenue).desc())
        .first()
    )

    # Revenue by product type
    type_breakdown = (
        db.query(Product.product_type, func.sum(Sale.gross_revenue).label("rev"))
        .join(Sale, Sale.product_id == Product.id)
        .group_by(Product.product_type)
        .all()
    )

    analytics = SalesAnalytics(
        total_revenue=float(totals.total_revenue or 0),
        total_profit=float(totals.total_profit or 0),
        total_orders=int(totals.total_orders or 0),
        best_seller_product_id=best_seller.product_id if best_seller else None,
        revenue_by_product_type={row.product_type: float(row.rev) for row in type_breakdown},
        weekly_trend=[],
    )
    return _envelope(analytics.model_dump())


@router.post("/sync")
def manual_sync(_: str = Depends(verify_api_key)):
    """Manually trigger Shopify sales sync."""
    from app.tasks.sales_sync import sync_shopify_sales
    task = sync_shopify_sales.delay()
    return _envelope({"task_id": task.id, "message": "Sales sync queued"})
