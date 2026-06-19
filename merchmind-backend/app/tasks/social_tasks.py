"""
Celery tasks for social media posting, called by SocialScheduler with eta.
Each task is idempotent: errors are logged but never re-raise to avoid Celery retries
on transient platform failures.
"""
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.post_to_instagram", bind=True, max_retries=2, default_retry_delay=300)
def post_to_instagram(
    self,
    image_url: str,
    caption: str,
    product_url: str,
    campaign: str,
    design_id: str,
) -> dict:
    try:
        from app.services.marketing.instagram_service import get_instagram_service
        svc = get_instagram_service()
        media_id = svc.schedule_post(
            image_url=image_url,
            caption=caption,
            product_url=product_url,
            campaign=campaign,
        )
        logger.info("social_tasks.post_to_instagram design_id=%s media_id=%s", design_id, media_id)
        return {"platform": "instagram", "media_id": media_id, "design_id": design_id}
    except Exception as e:
        logger.error("social_tasks.post_to_instagram failed design_id=%s error=%s", design_id, e)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"platform": "instagram", "error": str(e), "design_id": design_id}


@celery_app.task(name="tasks.post_to_tiktok", bind=True, max_retries=1, default_retry_delay=600)
def post_to_tiktok(
    self,
    video_url: str,
    caption: str,
    product_url: str,
    campaign: str,
    design_id: str,
) -> dict:
    try:
        from app.services.marketing.tiktok_service import get_tiktok_service
        svc = get_tiktok_service()
        post_id = svc.post_video(
            video_url=video_url,
            caption=caption,
            product_url=product_url,
            campaign=campaign,
        )
        logger.info("social_tasks.post_to_tiktok design_id=%s post_id=%s", design_id, post_id)
        return {"platform": "tiktok", "post_id": post_id, "design_id": design_id}
    except Exception as e:
        logger.warning("social_tasks.post_to_tiktok failed design_id=%s error=%s", design_id, e)
        return {"platform": "tiktok", "error": str(e), "design_id": design_id}


@celery_app.task(name="tasks.post_to_pinterest", bind=True, max_retries=2, default_retry_delay=300)
def post_to_pinterest(
    self,
    board_id: str,
    title: str,
    description: str,
    image_url: str,
    product_url: str,
    campaign: str,
    design_id: str,
) -> dict:
    try:
        from app.services.marketing.pinterest_service import get_pinterest_service
        svc = get_pinterest_service()
        pin_id = svc.create_pin(
            board_id=board_id,
            title=title,
            description=description,
            image_url=image_url,
            product_url=product_url,
            campaign=campaign,
        )
        logger.info("social_tasks.post_to_pinterest design_id=%s pin_id=%s", design_id, pin_id)
        return {"platform": "pinterest", "pin_id": pin_id, "design_id": design_id}
    except Exception as e:
        logger.error("social_tasks.post_to_pinterest failed design_id=%s error=%s", design_id, e)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"platform": "pinterest", "error": str(e), "design_id": design_id}


@celery_app.task(name="tasks.send_klaviyo_campaign", bind=True, max_retries=2, default_retry_delay=300)
def send_klaviyo_campaign(
    self,
    design_title: str,
    tagline: str,
    product_url: str,
    image_url: str,
    price: float,
    campaign: str,
    niche: str = "",
) -> dict:
    try:
        from app.services.marketing.klaviyo_service import get_klaviyo_service
        svc = get_klaviyo_service()
        html = svc.build_product_launch_email(
            design_title=design_title,
            tagline=tagline,
            product_url=product_url,
            image_url=image_url,
            price=price,
            campaign=campaign,
            niche=niche,
        )
        campaign_id = svc.create_campaign(
            subject=f"New Drop: {design_title}",
            preview_text=tagline,
            html_body=html,
        )
        logger.info("social_tasks.send_klaviyo_campaign campaign_id=%s title=%r", campaign_id, design_title)
        return {"platform": "klaviyo", "campaign_id": campaign_id}
    except Exception as e:
        logger.error("social_tasks.send_klaviyo_campaign failed title=%r error=%s", design_title, e)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"platform": "klaviyo", "error": str(e)}
