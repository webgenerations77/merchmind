from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class MerchDropCreate(BaseModel):
    name: str
    scheduled_at: datetime


class MerchDropUpdate(BaseModel):
    name: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class MerchDropOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    scheduled_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime


class MerchDropDetail(MerchDropOut):
    product_count: int = 0
    products: list[dict] = []
