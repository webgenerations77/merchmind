import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class MarketingAsset(Base):
    __tablename__ = "marketing_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    channel = Column(
        SAEnum("instagram", "tiktok", "pinterest", "email", "blog", name="marketing_channel"),
        nullable=False,
    )
    content = Column(JSONB, default=dict)
    status = Column(
        SAEnum("pending", "approved", "scheduled", "posted", "failed", name="asset_status"),
        nullable=False,
        default="pending",
    )
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    post_url = Column(Text, nullable=True)
    engagement = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    design = relationship("Design", back_populates="marketing_assets")
