import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(
        SAEnum(
            "batch_ready", "underperformer", "trend_drop", "publish_failed",
            "api_down", "empty_batch", "margin_warning", "risk_flag",
            name="alert_type",
        ),
        nullable=False,
    )
    severity = Column(
        SAEnum("info", "warning", "critical", name="alert_severity"),
        nullable=False,
    )
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    message = Column(Text, nullable=False)
    action_url = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="alerts")
    design = relationship("Design", back_populates="alerts")
    batch = relationship("Batch", back_populates="alerts")
