import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String(50), nullable=False)
    operation = Column(String(100), nullable=False)
    model = Column(String(100), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Numeric(10, 6), nullable=False, default=0)
    design_id = Column(UUID(as_uuid=True), nullable=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    collection_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
