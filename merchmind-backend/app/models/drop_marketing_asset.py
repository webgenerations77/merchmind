import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class DropMarketingAsset(Base):
    __tablename__ = "drop_marketing_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drop_id = Column(UUID(as_uuid=True), ForeignKey("merch_drops.id"), nullable=False)
    channel = Column(
        SAEnum(
            "instagram", "tiktok", "pinterest", "email", "blog",
            name="marketing_channel",
            create_type=False,
        ),
        nullable=False,
    )
    content = Column(JSONB, default=dict)
    status = Column(
        SAEnum(
            "pending", "approved", "scheduled", "posted", "failed",
            name="asset_status",
            create_type=False,
        ),
        nullable=False,
        default="pending",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    merch_drop = relationship("MerchDrop", back_populates="marketing_assets")
