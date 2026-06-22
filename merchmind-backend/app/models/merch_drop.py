import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class MerchDrop(Base):
    __tablename__ = "merch_drops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        SAEnum(
            "scheduled", "in_progress", "published", "failed",
            name="drop_status",
        ),
        nullable=False,
        default="scheduled",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = relationship("Product", back_populates="merch_drop")
    marketing_assets = relationship("DropMarketingAsset", back_populates="merch_drop", cascade="all, delete-orphan")
