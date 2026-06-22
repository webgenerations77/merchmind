from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_id: UUID
    product_type: str
    printify_product_id: Optional[str]
    shopify_product_id: Optional[str]
    printify_base_cost: float
    base_markup: float
    trend_adjustment: float
    retail_price: float
    floor_price: float
    margin_flag: bool
    variants: Optional[list]
    mockup_urls: Optional[dict]
    publish_status: str
    published_at: Optional[datetime]
    unpublished_at: Optional[datetime]
    drop_id: Optional[UUID] = None
    created_at: datetime


class ProductUpdate(BaseModel):
    retail_price: Optional[float] = None
    publish_status: Optional[str] = None
