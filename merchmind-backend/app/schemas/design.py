from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, Any
from uuid import UUID


class DesignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trend_id: Optional[UUID]
    batch_id: Optional[UUID]
    collection_id: Optional[UUID] = None
    concept_name: str
    archetype: str
    image_api_used: Optional[str]
    image_prompt: Optional[str]
    raw_image_url: Optional[str]
    processed_image_url: Optional[str]
    font_pair: Optional[str]
    font_reasoning: Optional[str]
    color_palette: Optional[list]
    primary_text: Optional[str] = None
    secondary_text: Optional[str] = None
    tagline: Optional[str] = None
    text_concept_scoring: Optional[dict] = None
    design_style: Optional[str]
    quality_score: int
    quality_breakdown: Optional[dict]
    version: int
    parent_design_id: Optional[UUID]
    shopify_title: Optional[str]
    shopify_description: Optional[str]
    shopify_tags: Optional[list]
    classification: Optional[str] = "design_idea"
    primary_product_type: Optional[str] = "tshirt"
    primary_product_type_reasoning: Optional[str] = None
    is_featured: bool = False
    featured_at: Optional[datetime] = None
    conversation_history: Optional[list] = None
    status: str
    delayed_to_week: Optional[date]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    archived_at: Optional[datetime] = None
    revisit_count: Optional[int] = 0
    created_at: datetime


class DesignQueueItem(BaseModel):
    """Lightweight design card for the mobile review queue."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: Optional[UUID] = None
    concept_name: str
    archetype: str
    processed_image_url: Optional[str]
    quality_score: int
    shopify_title: Optional[str]
    classification: Optional[str] = "design_idea"
    status: str
    collection_id: Optional[UUID] = None
    primary_product_type: Optional[str] = "tshirt"
    image_api_used: Optional[str] = None
    is_featured: bool = False
    revisit_count: Optional[int] = 0
    claude_reasoning: Optional[str] = None


class DelayRequest(BaseModel):
    delayed_to_week: date


class RegenerateRequest(BaseModel):
    new_prompt: Optional[str] = None
    force_archetype: Optional[str] = None


class ChatMessageIn(BaseModel):
    message: str


class SuggestRegenerateRequest(BaseModel):
    conversation: list[dict]
    vibe: Optional[list[str]] = None
    change_focus: Optional[str] = None
    audience: Optional[list[str]] = None
