import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class CustomIdea(Base):
    __tablename__ = "custom_ideas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_text = Column(Text, nullable=False)
    source = Column(String(50), default="drews_mind")
    design_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(
        SAEnum("pending", "generating", "complete", "failed", name="idea_status"),
        nullable=False,
        default="pending",
    )
    preferences = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
