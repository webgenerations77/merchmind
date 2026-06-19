"""
Twitter/X scraper — class-based wrapper around tweepy.
Gracefully degrades when account API tier is insufficient (Basic or lower).
Never crashes the pipeline — logs a warning and returns empty results.
"""
import logging
from functools import lru_cache
import tweepy

from app.config import settings
from app.utils.exceptions import TwitterScraperError, TikTokAPITierError

logger = logging.getLogger(__name__)

_MIN_ENGAGEMENT = 500
_TWEET_LIMIT = 50
_US_WOEID = 23424977  # Yahoo WOEID for United States

_TIER_WARNING = (
    "Twitter API call skipped — account tier does not support this endpoint. "
    "Upgrade to Elevated/Academic access to enable Twitter signals."
)


class TwitterScraperService:
    def __init__(self) -> None:
        self._client: tweepy.Client | None = None
        self._api: tweepy.API | None = None

    def _get_clients(self) -> tuple[tweepy.Client, tweepy.API]:
        if self._client is None:
            self._client = tweepy.Client(
                bearer_token=getattr(settings, "TWITTER_BEARER_TOKEN", ""),
                wait_on_rate_limit=True,
            )
        if self._api is None:
            auth = tweepy.OAuth1UserHandler(
                consumer_key=getattr(settings, "TWITTER_CONSUMER_KEY", ""),
                consumer_secret=getattr(settings, "TWITTER_CONSUMER_SECRET", ""),
                access_token=getattr(settings, "TWITTER_ACCESS_TOKEN", ""),
                access_token_secret=getattr(settings, "TWITTER_ACCESS_SECRET", ""),
            )
            self._api = tweepy.API(auth, timeout=30, wait_on_rate_limit=True)
        return self._client, self._api

    def _is_tier_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        return "403" in msg or "401" in msg or "client-not-enrolled" in msg or "not permitted" in msg

    def get_us_trends(self) -> list[dict]:
        """
        Fetch US trending topics. Returns [] with a warning on tier errors — never raises.
        """
        results = []
        try:
            _, api = self._get_clients()
            trends_result = api.get_place_trends(_US_WOEID)
            for trend in trends_result[0]["trends"]:
                tweet_volume = trend.get("tweet_volume") or 0
                results.append({
                    "raw_signal": trend["name"],
                    "source": "twitter",
                    "source_metadata": {
                        "type": "trending_topic",
                        "tweet_volume": tweet_volume,
                        "url": trend.get("url", ""),
                    },
                })
            logger.info("twitter.get_us_trends count=%d", len(results))
        except Exception as e:
            if self._is_tier_error(e):
                logger.warning("twitter.get_us_trends %s", _TIER_WARNING)
            else:
                logger.error("twitter.get_us_trends failed error=%s", e)
        return results

    def get_keyword_tweets(self, keywords: list[str], cluster_name: str) -> list[dict]:
        """
        Search recent tweets for niche keywords. Returns [] with a warning on tier errors.
        """
        results = []
        try:
            client, _ = self._get_clients()
            for keyword in keywords:
                query = f"{keyword} -is:retweet lang:en"
                response = client.search_recent_tweets(
                    query=query,
                    max_results=min(_TWEET_LIMIT, 100),
                    tweet_fields=["public_metrics", "text"],
                )
                if not response.data:
                    continue
                for tweet in response.data:
                    metrics = tweet.public_metrics or {}
                    engagement = (
                        metrics.get("like_count", 0)
                        + metrics.get("retweet_count", 0)
                        + metrics.get("reply_count", 0)
                    )
                    if engagement < _MIN_ENGAGEMENT:
                        continue
                    results.append({
                        "raw_signal": tweet.text[:200],
                        "source": "twitter",
                        "source_url": f"https://twitter.com/i/web/status/{tweet.id}",
                        "source_metadata": {
                            "cluster": cluster_name,
                            "seed_keyword": keyword,
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "engagement": engagement,
                        },
                    })
        except Exception as e:
            if self._is_tier_error(e):
                logger.warning("twitter.get_keyword_tweets %s", _TIER_WARNING)
            else:
                logger.error("twitter.get_keyword_tweets failed cluster=%s error=%s", cluster_name, e)

        logger.info("twitter.get_keyword_tweets cluster=%s count=%d", cluster_name, len(results))
        return results

    def health_check(self) -> dict:
        try:
            client, _ = self._get_clients()
            # me() is available on all API tiers
            client.get_me()
            return {"service": "twitter", "ok": True}
        except Exception as e:
            if self._is_tier_error(e):
                logger.warning("twitter.health_check tier insufficient error=%s", e)
                return {"service": "twitter", "ok": False, "error": "API tier insufficient", "degraded": True}
            logger.warning("twitter.health_check failed error=%s", e)
            return {"service": "twitter", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_twitter_scraper_service() -> TwitterScraperService:
    return TwitterScraperService()


# Module-level aliases for backwards compatibility
_svc: TwitterScraperService | None = None


def _get() -> TwitterScraperService:
    global _svc
    if _svc is None:
        _svc = TwitterScraperService()
    return _svc


def fetch_us_trends() -> list[dict]:
    return _get().get_us_trends()


def fetch_keyword_tweets(keywords: list[str], cluster_name: str) -> list[dict]:
    return _get().get_keyword_tweets(keywords, cluster_name)
