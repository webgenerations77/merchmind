import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base


class NicheCluster(Base):
    __tablename__ = "niche_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False)
    subreddits = Column(ARRAY(Text), default=list)
    keywords = Column(ARRAY(Text), default=list)
    score_boost = Column(Integer, default=15)
    active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
