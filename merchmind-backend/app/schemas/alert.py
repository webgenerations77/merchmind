from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    severity: str
    product_id: Optional[UUID]
    design_id: Optional[UUID]
    batch_id: Optional[UUID]
    message: str
    action_url: Optional[str]
    resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime
