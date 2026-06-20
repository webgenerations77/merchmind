import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class Design(Base):
    __tablename__ = "designs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_id = Column(UUID(as_uuid=True), ForeignKey("trends.id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    concept_name = Column(Text, nullable=False)
    archetype = Column(
        SAEnum(
            "text_only", "illustration", "hybrid", "typographic", "text_icon",
            name="design_archetype",
        ),
        nullable=False,
    )
    image_api_used = Column(
        SAEnum("dalle3", "stable_diffusion", "flux_schnell", name="image_api"),
        nullable=True,
    )
    image_prompt = Column(Text, nullable=True)
    raw_image_url = Column(Text, nullable=True)
    processed_image_url = Column(Text, nullable=True)
    font_pair = Column(Text, nullable=True)
    font_reasoning = Column(Text, nullable=True)
    color_palette = Column(JSONB, default=list)
    design_style = Column(Text, nullable=True)
    quality_score = Column(Integer, default=0)
    quality_breakdown = Column(JSONB, default=dict)
    version = Column(Integer, default=1)
    parent_design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=True)
    shopify_title = Column(Text, nullable=True)
    shopify_description = Column(Text, nullable=True)
    shopify_tags = Column(ARRAY(Text), default=list)
    is_deleted = Column(Boolean, default=False)
    status = Column(
        SAEnum(
            "generating", "ready", "approved", "rejected", "delayed",
            name="design_status",
        ),
        nullable=False,
        default="generating",
    )
    delayed_to_week = Column(Date, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    trend = relationship("Trend", back_populates="designs")
    batch = relationship("Batch", back_populates="designs")
    products = relationship("Product", back_populates="design")
    marketing_assets = relationship("MarketingAsset", back_populates="design")
    feedback_logs = relationship("FeedbackLog", back_populates="design")
    alerts = relationship("Alert", back_populates="design")
    versions = relationship(
        "Design",
        primaryjoin="Design.parent_design_id == Design.id",
        foreign_keys="Design.parent_design_id",
    )
