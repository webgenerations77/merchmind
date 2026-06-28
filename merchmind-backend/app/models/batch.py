import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Date, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start = Column(Date, nullable=False)
    run_started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    run_completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        SAEnum("running", "complete", "failed", "partial", "pending_approval", name="batch_status"),
        nullable=False,
        default="running",
    )
    total_ideas = Column(Integer, default=0)
    queued_count = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    delayed_count = Column(Integer, default=0)
    error_log = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    trends = relationship("Trend", back_populates="batch")
    designs = relationship("Design", back_populates="batch")
    alerts = relationship("Alert", back_populates="batch")
    items = relationship("BatchItem", back_populates="batch", order_by="BatchItem.created_at")
