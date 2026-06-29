"""
MerchMind FastAPI application entry point.
"""
import logging
import logging.config
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text as sa_text

from app.config import settings
from app.utils.error_handler import (
    MerchMindError,
    merchmind_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
import app.models  # noqa: F401 — ensure all models are registered before routers
from app.routers import (
    api_usage,
    batches,
    collections,
    designs,
    drops,
    products,
    sales,
    alerts,
    niche_clusters,
    marketing,
    settings as settings_router,
    onboarding,
    health,
    custom_ideas,
    trends,
)

# JSON structured logging for Railway log aggregation
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
})

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MerchMind API",
    version="1.0.0",
    description="Automated print-on-demand merchandise pipeline backend",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(MerchMindError, merchmind_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(api_usage.router)
app.include_router(batches.router)
app.include_router(collections.router)
app.include_router(designs.router)
app.include_router(drops.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(alerts.router)
app.include_router(niche_clusters.router)
app.include_router(marketing.router)
app.include_router(settings_router.router)
app.include_router(onboarding.router)
app.include_router(health.router)
app.include_router(custom_ideas.router)
app.include_router(trends.router)


@app.on_event("startup")
async def on_startup():
    logger.info("MerchMind API starting", extra={"environment": settings.ENVIRONMENT})
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied")
    except Exception as e:
        logger.warning(f"Alembic migration skipped: {e}")
    # Always run the schema fallback — idempotent IF NOT EXISTS guards make it safe.
    # This catches cases where a migration ran but its DDL didn't commit (COMMIT/BEGIN pattern).
    _apply_critical_schema_fallback()


def _apply_critical_schema_fallback():
    """Ensure critical tables/columns exist if Alembic migration failed."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        conn = db.connection()
        # Enum additions must run outside a transaction on some PostgreSQL versions.
        conn.execute(sa_text("COMMIT"))
        conn.execute(sa_text("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'hoodie'"))
        conn.execute(sa_text("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'long_sleeve'"))
        conn.execute(sa_text("ALTER TYPE design_archetype ADD VALUE IF NOT EXISTS 'image_with_text'"))
        conn.execute(sa_text("ALTER TYPE image_api ADD VALUE IF NOT EXISTS 'ideogram'"))
        conn.execute(sa_text("ALTER TYPE batch_status ADD VALUE IF NOT EXISTS 'pending_approval'"))
        conn.execute(sa_text("ALTER TYPE design_status ADD VALUE IF NOT EXISTS 'generation_failed'"))
        conn.execute(sa_text("ALTER TYPE trend_source ADD VALUE IF NOT EXISTS 'firecrawl'"))
        conn.execute(sa_text("BEGIN"))
        # Migration 023: trend approval gate + store selection columns
        conn.execute(sa_text(
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'pending_review'"
        ))
        conn.execute(sa_text(
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS selected_generator VARCHAR(50)"
        ))
        conn.execute(sa_text(
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS proposed_archetype VARCHAR(50)"
        ))
        conn.execute(sa_text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS target_store VARCHAR(10) DEFAULT 'store_1'"
        ))
        conn.execute(sa_text(
            "DO $$ BEGIN "
            "  CREATE TYPE drop_status AS ENUM ('scheduled','in_progress','published','failed'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        ))
        conn.execute(sa_text(
            "CREATE TABLE IF NOT EXISTS merch_drops ("
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "  name TEXT NOT NULL,"
            "  scheduled_at TIMESTAMPTZ NOT NULL,"
            "  status drop_status NOT NULL DEFAULT 'scheduled',"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        ))
        conn.execute(sa_text(
            "DO $$ BEGIN "
            "  ALTER TABLE products ADD COLUMN drop_id UUID REFERENCES merch_drops(id); "
            "EXCEPTION WHEN duplicate_column THEN NULL; END $$;"
        ))
        conn.execute(sa_text(
            "CREATE TABLE IF NOT EXISTS drop_marketing_assets ("
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "  drop_id UUID NOT NULL REFERENCES merch_drops(id),"
            "  channel marketing_channel NOT NULL,"
            "  content JSONB DEFAULT '{}',"
            "  status asset_status NOT NULL DEFAULT 'pending',"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        ))
        db.commit()
        logger.info("Critical schema fallback applied successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Schema fallback failed: {e}")
    finally:
        db.close()
