from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from uuid import UUID


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    week_start: date
    run_started_at: datetime
    run_completed_at: Optional[datetime]
    status: str
    total_ideas: int
    queued_count: int
    approved_count: int
    rejected_count: int
    delayed_count: int
    error_log: list
    created_at: datetime


class BatchListOut(BaseModel):
    batches: list[BatchOut]
    total: int


class BatchItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    trend_id: Optional[UUID]
    design_id: Optional[UUID]
    concept_name: str
    status: str
    failed_step: Optional[str]
    error_summary: Optional[str]
    error_detail: Optional[str]
    product_types: list[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    processed_image_url: Optional[str] = None


class BatchDetailOut(BaseModel):
    batch: BatchOut
    items: list[BatchItemOut]
    success_count: int
    failed_count: int
