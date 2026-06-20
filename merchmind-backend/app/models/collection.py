import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    style_guide = Column(JSONB, nullable=False, default=dict)
    max_designs = Column(Integer, nullable=False, default=6)
    status = Column(
        SAEnum("draft", "generating", "ready", "published", name="collection_status"),
        nullable=False,
        default="draft",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    designs = relationship("Design", back_populates="collection")
