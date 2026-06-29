"""Periodic Printify catalog refresh."""
import logging

from app.services.catalog.catalog_service import get_catalog_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.catalog_refresh.refresh_printify_catalog")
def refresh_printify_catalog():
    logger.info("catalog.refresh_task starting")
    get_catalog_service().refresh()
    logger.info("catalog.refresh_task done")
