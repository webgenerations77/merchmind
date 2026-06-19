from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from uuid import UUID


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    shopify_order_id: str
    quantity: int
    gross_revenue: float
    printify_cost: float
    net_profit: float
    sale_date: date
    variant: Optional[str]
    created_at: datetime


class SalesAnalytics(BaseModel):
    total_revenue: float
    total_profit: float
    total_orders: int
    best_seller_product_id: Optional[UUID]
    revenue_by_product_type: dict
    weekly_trend: list[dict]
