"""
MerchMind FastAPI application entry point.
"""
import logging
import logging.config
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
