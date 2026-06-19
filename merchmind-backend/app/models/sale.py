import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Date, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    shopify_order_id = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    gross_revenue = Column(Numeric(10, 2), nullable=False)
    printify_cost = Column(Numeric(10, 2), nullable=False)
    net_profit = Column(Numeric(10, 2), nullable=False)
    sale_date = Column(Date, nullable=False)
    variant = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")
