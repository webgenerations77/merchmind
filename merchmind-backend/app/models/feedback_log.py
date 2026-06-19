import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, Date, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    action = Column(
        SAEnum("approved", "rejected", "delayed", "regenerated", name="feedback_action"),
        nullable=False,
    )
    original_prompt = Column(Text, nullable=False)
    edited_prompt = Column(Text, nullable=True)
    font_overridden = Column(Boolean, default=False)
    products_modified = Column(JSONB, default=dict)
    price_overridden = Column(Boolean, default=False)
    week = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    design = relationship("Design", back_populates="feedback_logs")
