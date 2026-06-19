"""Initial schema with all tables and seed data.

Revision ID: 001
Revises:
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
import json
from datetime import datetime, time

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

_NICHE_CLUSTERS = [
    {
        "id": str(uuid.uuid4()),
        "name": "Pet Obsessed",
        "emoji": "🐾",
        "subreddits": ["dogs", "cats", "AnimalsBeingDerps", "corgi", "goldenretrievers"],
        "keywords": ["dog mom", "cat dad", "fur baby", "golden retriever", "corgi", "dachshund"],
        "score_boost": 15,
        "active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Work & Hustle Humor",
        "emoji": "☕",
        "subreddits": ["antiwork", "WorkReform", "nurses", "Teachers", "cscareerquestions"],
        "keywords": ["Monday", "coffee", "overtime", "I survived", "meetings", "adulting"],
        "score_boost": 15,
        "active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Outdoor & Adventure",
        "emoji": "🌿",
        "subreddits": ["hiking", "camping", "climbing", "MountainBiking", "NationalParks"],
        "keywords": ["trail life", "summit", "van life", "leave no trace", "nature heals"],
        "score_boost": 15,
        "active": False,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Gamer & Nerd Culture",
        "emoji": "🎮",
        "subreddits": ["gaming", "pcmasterrace", "DnD", "boardgames", "anime"],
        "keywords": ["GG", "respawn", "critical hit", "level up", "nerd", "geek pride"],
        "score_boost": 15,
        "active": False,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Wellness & Mindset",
        "emoji": "🧘",
        "subreddits": ["Meditation", "yoga", "running", "loseit", "getdisciplined"],
        "keywords": ["mental health", "self care", "growth mindset", "marathon", "marathon mom"],
        "score_boost": 15,
        "active": False,
    },
]


def upgrade() -> None:
    # Create ENUMs
    op.execute("CREATE TYPE trend_source AS ENUM ('google', 'reddit', 'twitter', 'seasonal', 'manual')")
    op.execute("CREATE TYPE trend_risk_flag AS ENUM ('none', 'soft', 'hard')")
    op.execute("CREATE TYPE trend_status AS ENUM ('raw', 'scored', 'queued', 'rejected', 'used')")
    op.execute("CREATE TYPE batch_status AS ENUM ('running', 'complete', 'failed', 'partial')")
    op.execute("CREATE TYPE design_archetype AS ENUM ('text_only', 'illustration', 'hybrid', 'typographic', 'text_icon')")
    op.execute("CREATE TYPE image_api AS ENUM ('dalle3', 'stable_diffusion')")
    op.execute("CREATE TYPE design_status AS ENUM ('generating', 'ready', 'approved', 'rejected', 'delayed')")
    op.execute("CREATE TYPE product_type AS ENUM ('tshirt', 'mug', 'hat', 'phone_case', 'sticker', 'poster')")
    op.execute("CREATE TYPE publish_status AS ENUM ('pending', 'printify_only', 'live', 'failed', 'unpublished')")
    op.execute("CREATE TYPE alert_type AS ENUM ('batch_ready', 'underperformer', 'trend_drop', 'publish_failed', 'api_down', 'empty_batch', 'margin_warning', 'risk_flag')")
    op.execute("CREATE TYPE alert_severity AS ENUM ('info', 'warning', 'critical')")
    op.execute("CREATE TYPE feedback_action AS ENUM ('approved', 'rejected', 'delayed', 'regenerated')")
    op.execute("CREATE TYPE marketing_channel AS ENUM ('instagram', 'tiktok', 'pinterest', 'email', 'blog')")
    op.execute("CREATE TYPE asset_status AS ENUM ('pending', 'approved', 'scheduled', 'posted', 'failed')")
    op.execute("CREATE TYPE subscriber_status AS ENUM ('active', 'unsubscribed')")

    # niche_clusters
    op.create_table(
        "niche_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("emoji", sa.Text, nullable=False),
        sa.Column("subreddits", postgresql.ARRAY(sa.Text), default=[]),
        sa.Column("keywords", postgresql.ARRAY(sa.Text), default=[]),
        sa.Column("score_boost", sa.Integer, default=15),
        sa.Column("active", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # batches
    op.create_table(
        "batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("running", "complete", "failed", "partial", name="batch_status"), nullable=False),
        sa.Column("total_ideas", sa.Integer, default=0),
        sa.Column("queued_count", sa.Integer, default=0),
        sa.Column("approved_count", sa.Integer, default=0),
        sa.Column("rejected_count", sa.Integer, default=0),
        sa.Column("delayed_count", sa.Integer, default=0),
        sa.Column("error_log", postgresql.JSONB, default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # trends
    op.create_table(
        "trends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.Enum("google", "reddit", "twitter", "seasonal", "manual", name="trend_source"), nullable=False),
        sa.Column("raw_signal", sa.Text, nullable=False),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_metadata", postgresql.JSONB, default={}),
        sa.Column("trend_score", sa.Integer, default=0),
        sa.Column("viability_score", sa.Integer, default=0),
        sa.Column("final_score", sa.Integer, default=0),
        sa.Column("claude_reasoning", sa.Text, nullable=True),
        sa.Column("niche_cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("niche_clusters.id"), nullable=True),
        sa.Column("risk_flag", sa.Enum("none", "soft", "hard", name="trend_risk_flag"), nullable=False, default="none"),
        sa.Column("risk_reason", sa.Text, nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("status", sa.Enum("raw", "scored", "queued", "rejected", "used", name="trend_status"), nullable=False, default="raw"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # designs
    op.create_table(
        "designs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trends.id"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("concept_name", sa.Text, nullable=False),
        sa.Column("archetype", sa.Enum("text_only", "illustration", "hybrid", "typographic", "text_icon", name="design_archetype"), nullable=False),
        sa.Column("image_api_used", sa.Enum("dalle3", "stable_diffusion", name="image_api"), nullable=True),
        sa.Column("image_prompt", sa.Text, nullable=True),
        sa.Column("raw_image_url", sa.Text, nullable=True),
        sa.Column("processed_image_url", sa.Text, nullable=True),
        sa.Column("font_pair", sa.Text, nullable=True),
        sa.Column("font_reasoning", sa.Text, nullable=True),
        sa.Column("color_palette", postgresql.JSONB, default=[]),
        sa.Column("design_style", sa.Text, nullable=True),
        sa.Column("quality_score", sa.Integer, default=0),
        sa.Column("quality_breakdown", postgresql.JSONB, default={}),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("parent_design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=True),
        sa.Column("shopify_title", sa.Text, nullable=True),
        sa.Column("shopify_description", sa.Text, nullable=True),
        sa.Column("shopify_tags", postgresql.ARRAY(sa.Text), default=[]),
        sa.Column("is_deleted", sa.Boolean, default=False),
        sa.Column("status", sa.Enum("generating", "ready", "approved", "rejected", "delayed", name="design_status"), nullable=False, default="generating"),
        sa.Column("delayed_to_week", sa.Date, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=False),
        sa.Column("product_type", sa.Enum("tshirt", "mug", "hat", "phone_case", "sticker", "poster", name="product_type"), nullable=False),
        sa.Column("printify_product_id", sa.Text, nullable=True),
        sa.Column("shopify_product_id", sa.Text, nullable=True),
        sa.Column("printify_base_cost", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("base_markup", sa.Numeric(10, 4), nullable=False, default=2.5),
        sa.Column("trend_adjustment", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("retail_price", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("floor_price", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("margin_flag", sa.Boolean, default=False),
        sa.Column("variants", postgresql.JSONB, default=[]),
        sa.Column("mockup_urls", postgresql.JSONB, default={}),
        sa.Column("publish_status", sa.Enum("pending", "printify_only", "live", "failed", "unpublished", name="publish_status"), nullable=False, default="pending"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # sales
    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("shopify_order_id", sa.Text, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, default=1),
        sa.Column("gross_revenue", sa.Numeric(10, 2), nullable=False),
        sa.Column("printify_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("net_profit", sa.Numeric(10, 2), nullable=False),
        sa.Column("sale_date", sa.Date, nullable=False),
        sa.Column("variant", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Enum("batch_ready", "underperformer", "trend_drop", "publish_failed", "api_down", "empty_batch", "margin_warning", "risk_flag", name="alert_type"), nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "critical", name="alert_severity"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("action_url", sa.Text, nullable=True),
        sa.Column("resolved", sa.Boolean, default=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # feedback_logs
    op.create_table(
        "feedback_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=False),
        sa.Column("action", sa.Enum("approved", "rejected", "delayed", "regenerated", name="feedback_action"), nullable=False),
        sa.Column("original_prompt", sa.Text, nullable=False),
        sa.Column("edited_prompt", sa.Text, nullable=True),
        sa.Column("font_overridden", sa.Boolean, default=False),
        sa.Column("products_modified", postgresql.JSONB, default={}),
        sa.Column("price_overridden", sa.Boolean, default=False),
        sa.Column("week", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # settings (single row)
    op.create_table(
        "settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_markup", postgresql.JSONB),
        sa.Column("floor_prices", postgresql.JSONB),
        sa.Column("trend_boost_max", sa.Numeric(5, 4), default=0.20),
        sa.Column("publish_time", sa.Time),
        sa.Column("batch_day", sa.Text, default="sunday"),
        sa.Column("batch_time", sa.Time),
        sa.Column("min_queue_size", sa.Integer, default=10),
        sa.Column("max_queue_size", sa.Integer, default=25),
        sa.Column("quality_threshold", sa.Integer, default=28),
        sa.Column("score_threshold", sa.Integer, default=35),
        sa.Column("underperform_weeks", sa.Integer, default=4),
        sa.Column("shopify_store_url", sa.Text, nullable=True),
        sa.Column("active_clusters", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # marketing_assets
    op.create_table(
        "marketing_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=False),
        sa.Column("channel", sa.Enum("instagram", "tiktok", "pinterest", "email", "blog", name="marketing_channel"), nullable=False),
        sa.Column("content", postgresql.JSONB, default={}),
        sa.Column("status", sa.Enum("pending", "approved", "scheduled", "posted", "failed", name="asset_status"), nullable=False, default="pending"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("post_url", sa.Text, nullable=True),
        sa.Column("engagement", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # email_subscribers
    op.create_table(
        "email_subscribers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("niche_clusters", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column("klaviyo_id", sa.Text, nullable=True),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("active", "unsubscribed", name="subscriber_status"), nullable=False, default="active"),
    )

    # Seed: niche clusters
    now = datetime.utcnow()
    conn = op.get_bind()
    for cluster in _NICHE_CLUSTERS:
        conn.execute(
            sa.text(
                "INSERT INTO niche_clusters "
                "(id, name, emoji, subreddits, keywords, score_boost, active, created_at) "
                "VALUES (:id, :name, :emoji, :subreddits, :keywords, :boost, :active, :created_at)"
            ),
            {
                "id": cluster["id"],
                "name": cluster["name"],
                "emoji": cluster["emoji"],
                "subreddits": cluster["subreddits"],
                "keywords": cluster["keywords"],
                "boost": cluster["score_boost"],
                "active": cluster["active"],
                "created_at": now,
            },
        )

    # Seed: default settings row
    active_cluster_ids = [c["id"] for c in _NICHE_CLUSTERS if c["active"]]
    # Build the ARRAY literal for UUIDs inline since SQLAlchemy text() doesn't cast list→uuid[]
    active_arr = "ARRAY[" + ", ".join(f"'{cid}'::uuid" for cid in active_cluster_ids) + "]"
    conn.execute(
        sa.text(
            "INSERT INTO settings "
            "(id, base_markup, floor_prices, trend_boost_max, publish_time, batch_day, batch_time, "
            "min_queue_size, max_queue_size, quality_threshold, score_threshold, underperform_weeks, "
            f"active_clusters, updated_at) "
            f"VALUES (:id, :base_markup::jsonb, :floor_prices::jsonb, :boost_max, :pub_time, "
            f":batch_day, :batch_time, :min_q, :max_q, :qual_thresh, :score_thresh, :underperf, "
            f"{active_arr}, :updated_at)"
        ),
        {
            "id": str(uuid.uuid4()),
            "base_markup": json.dumps({"tshirt": 2.5, "mug": 2.8, "hat": 2.5, "phone_case": 2.5, "sticker": 3.0, "poster": 2.5}),
            "floor_prices": json.dumps({"tshirt": 24.99, "mug": 18.99, "hat": 26.99, "phone_case": 22.99, "sticker": 6.99, "poster": 29.99}),
            "boost_max": 0.20,
            "pub_time": "09:00:00",
            "batch_day": "sunday",
            "batch_time": "22:00:00",
            "min_q": 10,
            "max_q": 25,
            "qual_thresh": 28,
            "score_thresh": 35,
            "underperf": 4,
            "updated_at": now,
        },
    )


def downgrade() -> None:
    op.drop_table("email_subscribers")
    op.drop_table("marketing_assets")
    op.drop_table("settings")
    op.drop_table("feedback_logs")
    op.drop_table("alerts")
    op.drop_table("sales")
    op.drop_table("products")
    op.drop_table("designs")
    op.drop_table("trends")
    op.drop_table("batches")
    op.drop_table("niche_clusters")
    for enum in [
        "subscriber_status", "asset_status", "marketing_channel",
        "feedback_action", "alert_severity", "alert_type",
        "publish_status", "product_type", "design_status", "image_api",
        "design_archetype", "batch_status", "trend_status",
        "trend_risk_flag", "trend_source",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
