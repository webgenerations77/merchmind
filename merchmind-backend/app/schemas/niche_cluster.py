from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class NicheClusterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    emoji: str
    subreddits: list[str]
    keywords: list[str]
    score_boost: int
    active: bool
    created_at: datetime


class NicheClusterCreate(BaseModel):
    name: str
    emoji: str
    subreddits: list[str] = []
    keywords: list[str] = []
    score_boost: int = 15
    active: bool = False


class NicheClusterUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    subreddits: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    score_boost: Optional[int] = None
    active: Optional[bool] = None
