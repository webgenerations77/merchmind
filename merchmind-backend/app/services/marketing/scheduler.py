"""
Social media post scheduler.
Picks optimal posting times per niche cluster and queues posts as Celery tasks with eta.
"""
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal

from app.utils.exceptions import PostingLimitExceededError, SchedulerError

logger = logging.getLogger(__name__)

Platform = Literal["instagram", "tiktok", "pinterest"]

# Optimal posting windows per niche (hour in US/Eastern time, 0-23)
_OPTIMAL_HOURS: dict[str, dict[Platform, list[int]]] = {
    "pets": {
        "instagram": [8, 12, 20],
        "tiktok": [14, 18, 20],
        "pinterest": [20, 21],
    },
    "fitness": {
        "instagram": [6, 7, 17, 18],
        "tiktok": [6, 12, 17],
        "pinterest": [8, 13, 21],
    },
    "nursing": {
        "instagram": [7, 12, 21],
        "tiktok": [19, 20, 21],
        "pinterest": [9, 20],
    },
    "humor": {
        "instagram": [9, 12, 21],
        "tiktok": [12, 15, 21],
        "pinterest": [14, 20],
    },
    "gaming": {
        "instagram": [15, 20, 22],
        "tiktok": [16, 20, 23],
        "pinterest": [13, 20],
    },
    "default": {
        "instagram": [9, 12, 18],
        "tiktok": [12, 15, 19],
        "pinterest": [14, 20],
    },
}

# Max posts per platform per day to avoid spam detection
_DAILY_LIMITS: dict[Platform, int] = {
    "instagram": 3,
    "tiktok": 4,
    "pinterest": 10,
}


class SocialScheduler:
    def get_optimal_time(
        self,
        platform: Platform,
        niche: str,
        base_time: datetime | None = None,
    ) -> datetime:
        """
        Return the next optimal posting time for the platform and niche.
        Falls back to 'default' niche if niche not in table.
        Times are returned in UTC.
        """
        base = base_time or datetime.now(tz=timezone.utc)
        niche_key = niche.lower().split()[0] if niche else "default"
        hours_table = _OPTIMAL_HOURS.get(niche_key, _OPTIMAL_HOURS["default"])
        optimal_hours = hours_table.get(platform, [12])

        # Find next optimal hour after base_time (Eastern = UTC-5)
        eastern_offset = timedelta(hours=-5)
        base_eastern = base + eastern_offset
        base_hour = base_eastern.hour

        for hour in sorted(optimal_hours):
            if hour > base_hour:
                candidate = base_eastern.replace(hour=hour, minute=0, second=0, microsecond=0)
                return candidate - eastern_offset  # convert back to UTC

        # All optimal hours passed today — pick first slot tomorrow
        tomorrow = base_eastern + timedelta(days=1)
        first_hour = sorted(optimal_hours)[0]
        candidate = tomorrow.replace(hour=first_hour, minute=0, second=0, microsecond=0)
        return candidate - eastern_offset

    def check_posting_limit(self, platform: Platform, posts_today: int) -> None:
        """Raise PostingLimitExceededError if daily limit reached."""
        limit = _DAILY_LIMITS.get(platform, 3)
        if posts_today >= limit:
            raise PostingLimitExceededError(
                f"Daily {platform} limit of {limit} posts reached ({posts_today} posted)"
            )

    def schedule_instagram_post(
        self,
        image_url: str,
        caption: str,
        product_url: str,
        campaign: str,
        design_id: str,
        niche: str = "default",
        eta: datetime | None = None,
        posts_today: int = 0,
    ) -> str:
        """Queue an Instagram post as a Celery task. Returns task ID."""
        from app.tasks.social_tasks import post_to_instagram
        self.check_posting_limit("instagram", posts_today)
        scheduled = eta or self.get_optimal_time("instagram", niche)
        task = post_to_instagram.apply_async(
            kwargs={
                "image_url": image_url,
                "caption": caption,
                "product_url": product_url,
                "campaign": campaign,
                "design_id": design_id,
            },
            eta=scheduled,
        )
        logger.info("scheduler.instagram design_id=%s eta=%s task_id=%s", design_id, scheduled.isoformat(), task.id)
        return task.id

    def schedule_tiktok_post(
        self,
        video_url: str,
        caption: str,
        product_url: str,
        campaign: str,
        design_id: str,
        niche: str = "default",
        eta: datetime | None = None,
        posts_today: int = 0,
    ) -> str | None:
        """Queue a TikTok post. Returns task ID or None if tier-limited."""
        from app.tasks.social_tasks import post_to_tiktok
        try:
            self.check_posting_limit("tiktok", posts_today)
        except PostingLimitExceededError:
            logger.warning("scheduler.tiktok limit exceeded design_id=%s", design_id)
            return None
        scheduled = eta or self.get_optimal_time("tiktok", niche)
        task = post_to_tiktok.apply_async(
            kwargs={
                "video_url": video_url,
                "caption": caption,
                "product_url": product_url,
                "campaign": campaign,
                "design_id": design_id,
            },
            eta=scheduled,
        )
        logger.info("scheduler.tiktok design_id=%s eta=%s task_id=%s", design_id, scheduled.isoformat(), task.id)
        return task.id

    def schedule_pinterest_pin(
        self,
        board_id: str,
        title: str,
        description: str,
        image_url: str,
        product_url: str,
        campaign: str,
        design_id: str,
        niche: str = "default",
        eta: datetime | None = None,
        posts_today: int = 0,
    ) -> str:
        """Queue a Pinterest pin. Returns task ID."""
        from app.tasks.social_tasks import post_to_pinterest
        self.check_posting_limit("pinterest", posts_today)
        scheduled = eta or self.get_optimal_time("pinterest", niche)
        task = post_to_pinterest.apply_async(
            kwargs={
                "board_id": board_id,
                "title": title,
                "description": description,
                "image_url": image_url,
                "product_url": product_url,
                "campaign": campaign,
                "design_id": design_id,
            },
            eta=scheduled,
        )
        logger.info("scheduler.pinterest design_id=%s eta=%s task_id=%s", design_id, scheduled.isoformat(), task.id)
        return task.id

    def schedule_email_campaign(
        self,
        design_title: str,
        tagline: str,
        product_url: str,
        image_url: str,
        price: float,
        campaign: str,
        niche: str = "",
        eta: datetime | None = None,
    ) -> str:
        """Queue a Klaviyo campaign. Returns task ID."""
        from app.tasks.social_tasks import send_klaviyo_campaign
        scheduled = eta or self.get_optimal_time("instagram", niche)  # use same window as IG
        task = send_klaviyo_campaign.apply_async(
            kwargs={
                "design_title": design_title,
                "tagline": tagline,
                "product_url": product_url,
                "image_url": image_url,
                "price": price,
                "campaign": campaign,
                "niche": niche,
            },
            eta=scheduled,
        )
        logger.info("scheduler.email design_title=%r eta=%s task_id=%s", design_title, scheduled.isoformat(), task.id)
        return task.id


@lru_cache(maxsize=1)
def get_social_scheduler() -> SocialScheduler:
    return SocialScheduler()
