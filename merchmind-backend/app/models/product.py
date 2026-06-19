import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    product_type = Column(
        SAEnum(
            "tshirt", "mug", "hat", "phone_case", "sticker", "poster",
            name="product_type",
        ),
        nullable=False,
    )
    printify_product_id = Column(Text, nullable=True)
    shopify_product_id = Column(Text, nullable=True)
    printify_base_cost = Column(Numeric(10, 2), nullable=False, default=0)
    base_markup = Column(Numeric(10, 4), nullable=False, default=2.5)
    trend_adjustment = Column(Numeric(10, 2), nullable=False, default=0)
    retail_price = Column(Numeric(10, 2), nullable=False, default=0)
    floor_price = Column(Numeric(10, 2), nullable=False, default=0)
    margin_flag = Column(Boolean, default=False)
    variants = Column(JSONB, default=list)
    mockup_urls = Column(JSONB, default=dict)
    publish_status = Column(
        SAEnum(
            "pending", "printify_only", "live", "failed", "unpublished",
            name="publish_status",
        ),
        nullable=False,
        default="pending",
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    unpublished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    design = relationship("Design", back_populates="products")
    sales = relationship("Sale", back_populates="product")
    alerts = relationship("Alert", back_populates="product")
