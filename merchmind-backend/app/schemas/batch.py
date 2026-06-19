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
