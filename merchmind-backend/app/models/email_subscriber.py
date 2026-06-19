import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base


class EmailSubscriber(Base):
    __tablename__ = "email_subscribers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    niche_clusters = Column(ARRAY(UUID(as_uuid=True)), default=list)
    klaviyo_id = Column(Text, nullable=True)
    subscribed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status = Column(
        SAEnum("active", "unsubscribed", name="subscriber_status"),
        nullable=False,
        default="active",
    )
