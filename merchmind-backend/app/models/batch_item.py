import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class BatchItem(Base):
    __tablename__ = "batch_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False, index=True)
    trend_id = Column(UUID(as_uuid=True), ForeignKey("trends.id"), nullable=True)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=True)
    concept_name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="running")  # running, success, failed
    failed_step = Column(String(50), nullable=True)  # scoring, archetype, image_generation, quality, products, mockups, marketing
    error_summary = Column(String(500), nullable=True)
    error_detail = Column(Text, nullable=True)
    product_types = Column(JSONB, default=list)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    batch = relationship("Batch", back_populates="items")
    trend = relationship("Trend", foreign_keys=[trend_id])
    design = relationship("Design", foreign_keys=[design_id])
