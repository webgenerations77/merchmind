import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Trend(Base):
    __tablename__ = "trends"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(
        SAEnum("google", "reddit", "twitter", "seasonal", "manual", name="trend_source"),
        nullable=False,
    )
    raw_signal = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    source_metadata = Column(JSONB, default=dict)
    trend_score = Column(Integer, default=0)
    viability_score = Column(Integer, default=0)
    final_score = Column(Integer, default=0)
    claude_reasoning = Column(Text, nullable=True)
    niche_cluster_id = Column(UUID(as_uuid=True), ForeignKey("niche_clusters.id"), nullable=True)
    risk_flag = Column(
        SAEnum("none", "soft", "hard", name="trend_risk_flag"),
        nullable=False,
        default="none",
    )
    risk_reason = Column(Text, nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    status = Column(
        SAEnum("raw", "scored", "queued", "rejected", "used", name="trend_status"),
        nullable=False,
        default="raw",
    )
    # Trend approval gate fields (migration 023)
    approval_status = Column(String, nullable=False, default="pending_review")
    selected_generator = Column(String, nullable=True)  # dalle3 | flux_schnell | ideogram | text_only
    proposed_archetype = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    batch = relationship("Batch", back_populates="trends")
    niche_cluster = relationship("NicheCluster")
    designs = relationship("Design", back_populates="trend")
