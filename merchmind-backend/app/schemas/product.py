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
    selected_color: Optional[str] = None
    color_mockups: Optional[dict] = None
    publish_status: str
    published_at: Optional[datetime]
    unpublished_at: Optional[datetime]
    drop_id: Optional[UUID] = None
    target_store: Optional[str] = "store_1"
    created_at: datetime
    concept_name: Optional[str] = None
    batch_id: Optional[UUID] = None
    processed_image_url: Optional[str] = None
    primary_mockup_url: Optional[str] = None


class ProductUpdate(BaseModel):
    retail_price: Optional[float] = None
    publish_status: Optional[str] = None
    target_store: Optional[str] = None
    selected_color: Optional[str] = None
