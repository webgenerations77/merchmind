from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class StyleGuide(BaseModel):
    palette: list[str] = []
    mood: str = ""
    constraints: str = ""
    archetype_override: Optional[str] = None


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    style_guide: dict = {}
    max_designs: int = 6


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    style_guide: Optional[dict] = None
    max_designs: Optional[int] = None
    status: Optional[str] = None


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    style_guide: dict
    max_designs: int
    status: str
    created_at: datetime
    updated_at: datetime


class CollectionWithDesigns(CollectionOut):
    design_count: int = 0
    designs: list[dict] = []
