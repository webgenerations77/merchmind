import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, DateTime, Time, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.database import Base


class AppSettings(Base):
    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_markup = Column(
        JSONB,
        default=lambda: {
            "tshirt": 2.5, "mug": 2.8, "hat": 2.5,
            "phone_case": 2.5, "sticker": 3.0, "poster": 2.5,
        },
    )
    floor_prices = Column(
        JSONB,
        default=lambda: {
            "tshirt": 24.99, "mug": 18.99, "hat": 26.99,
            "phone_case": 22.99, "sticker": 6.99, "poster": 29.99,
        },
    )
    trend_boost_max = Column(Numeric(5, 4), default=0.20)
    publish_time = Column(Time, default="09:00:00")
    batch_day = Column(Text, default="sunday")
    batch_time = Column(Time, default="22:00:00")
    min_queue_size = Column(Integer, default=10)
    max_queue_size = Column(Integer, default=25)
    quality_threshold = Column(Integer, default=28)
    score_threshold = Column(Integer, default=35)
    underperform_weeks = Column(Integer, default=4)
    shopify_store_url = Column(Text, nullable=True)
    back_logo_enabled = Column(Boolean, default=False, nullable=False)
    back_logo_url = Column(Text, nullable=True)
    back_logo_products = Column(JSONB, default=lambda: ["tshirt", "hat"])
    active_clusters = Column(ARRAY(UUID(as_uuid=True)), default=list)
    marketing_generation_enabled = Column(Boolean, default=False, nullable=False)
    social_links = Column(JSONB, default=lambda: {
        "instagram_url": "", "tiktok_url": "", "pinterest_url": "", "facebook_url": "",
    })
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
