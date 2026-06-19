from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any
from uuid import UUID


class MarketingAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_id: UUID
    channel: str
    content: dict
    status: str
    scheduled_for: Optional[datetime]
    posted_at: Optional[datetime]
    post_url: Optional[str]
    engagement: Optional[dict]
    created_at: datetime


class MarketingAssetUpdate(BaseModel):
    content: Optional[dict] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None
