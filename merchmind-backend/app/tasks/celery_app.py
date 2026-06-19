"""
Celery application configuration with Beat schedule.
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "merchmind",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.batch_pipeline",
        "app.tasks.publish_queue",
        "app.tasks.sales_sync",
        "app.tasks.underperformer_check",
        "app.tasks.analytics_sync",
        "app.tasks.health_monitor",
        "app.tasks.social_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,                  # Prevent lost tasks on worker restart
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    task_default_retry_delay=30,
    # Retry policy defaults applied in task decorators
    task_annotations={
        "*": {
            "max_retries": 3,
            "default_retry_delay": 30,
        }
    },
)

celery_app.conf.beat_schedule = {
    "sunday-batch": {
        "task": "app.tasks.batch_pipeline.run_weekly_batch",
        "schedule": crontab(hour=22, minute=0, day_of_week=0),  # Sunday 10pm UTC
    },
    "monday-publish": {
        "task": "app.tasks.publish_queue.publish_approved_products",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),   # Monday 9am UTC
    },
    "weekly-sales-sync": {
        "task": "app.tasks.sales_sync.sync_shopify_sales",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),   # Monday 6am UTC
    },
    "underperformer-check": {
        "task": "app.tasks.underperformer_check.check_underperformers",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),   # Monday 7am UTC
    },
    "analytics-sync": {
        "task": "tasks.analytics_sync",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),   # Monday 6am UTC
    },
    "health-monitor": {
        "task": "tasks.health_monitor",
        "schedule": crontab(minute=0, hour="*/6"),               # Every 6 hours
    },
}
