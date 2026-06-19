from pydantic import BaseModel, ConfigDict
from datetime import datetime, time
from typing import Optional
from uuid import UUID


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    base_markup: dict
    floor_prices: dict
    trend_boost_max: float
    publish_time: Optional[time]
    batch_day: str
    batch_time: Optional[time]
    min_queue_size: int
    max_queue_size: int
    quality_threshold: int
    score_threshold: int
    underperform_weeks: int
    shopify_store_url: Optional[str]
    active_clusters: Optional[list]
    updated_at: datetime


class SettingsUpdate(BaseModel):
    base_markup: Optional[dict] = None
    floor_prices: Optional[dict] = None
    trend_boost_max: Optional[float] = None
    min_queue_size: Optional[int] = None
    max_queue_size: Optional[int] = None
    quality_threshold: Optional[int] = None
    score_threshold: Optional[int] = None
    underperform_weeks: Optional[int] = None
    shopify_store_url: Optional[str] = None
    active_clusters: Optional[list] = None
