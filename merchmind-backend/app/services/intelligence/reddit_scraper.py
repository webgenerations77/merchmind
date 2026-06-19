"""
Reddit scraper — class-based wrapper around PRAW.
Fetches top posts from niche cluster subreddits and extracts merch themes via Claude Haiku.
"""
import logging
from functools import lru_cache
import praw

from app.config import settings
from app.utils.claude_client import claude
from app.utils.exceptions import RedditScraperError

logger = logging.getLogger(__name__)

_SCORE_THRESHOLD = 100
_POST_LIMIT = 25


class RedditScraperService:
    def __init__(self) -> None:
        self._reddit: praw.Reddit | None = None

    def _get_reddit(self) -> praw.Reddit:
        if self._reddit is None:
            self._reddit = praw.Reddit(
                client_id=getattr(settings, "REDDIT_CLIENT_ID", ""),
                client_secret=getattr(settings, "REDDIT_CLIENT_SECRET", ""),
                user_agent="MerchMind/1.0 trend-scraper",
                requestor_kwargs={"timeout": 30},
            )
        return self._reddit

    def _extract_theme(self, title: str, subreddit: str) -> str:
        prompt = (
            f"Reddit post title from r/{subreddit}: \"{title}\"\n\n"
            "In one short phrase (3-8 words), identify the underlying topic or theme "
            "that could translate to print-on-demand merchandise. "
            "Be specific and concrete. Reply with ONLY the theme phrase."
        )
        try:
            text, _ = claude.haiku(
                "reddit_theme_extraction",
                [{"role": "user", "content": prompt}],
                max_tokens=32,
            )
            return text.strip().strip('"')
        except Exception as e:
            logger.warning("reddit.extract_theme failed title=%r error=%s", title[:60], e)
            return title[:80]

    def get_subreddit_signals(
        self,
        subreddits: list[str],
        cluster_name: str,
        time_filter: str = "week",
    ) -> list[dict]:
        """
        Fetch top posts from subreddits and extract merch themes.
        Returns list of {raw_signal, source_metadata, source_url} dicts.
        """
        results = []
        reddit = self._get_reddit()

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                posts = subreddit.top(time_filter=time_filter, limit=_POST_LIMIT)
                count = 0
                for post in posts:
                    if post.score < _SCORE_THRESHOLD:
                        continue
                    if post.is_self and post.crosspost_parent_list:
                        continue
                    theme = self._extract_theme(post.title, sub_name)
                    results.append({
                        "raw_signal": theme,
                        "source": "reddit",
                        "source_url": f"https://reddit.com{post.permalink}",
                        "source_metadata": {
                            "subreddit": sub_name,
                            "cluster": cluster_name,
                            "post_title": post.title,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                        },
                    })
                    count += 1
                logger.info("reddit.subreddit r/%s cluster=%s signals=%d", sub_name, cluster_name, count)
            except Exception as e:
                logger.error("reddit.subreddit failed sub=%s error=%s", sub_name, e)

        logger.info("reddit.get_subreddit_signals cluster=%s total=%d", cluster_name, len(results))
        return results

    def health_check(self) -> dict:
        try:
            reddit = self._get_reddit()
            sub = reddit.subreddit("popular")
            _ = sub.display_name
            return {"service": "reddit", "ok": True}
        except Exception as e:
            logger.warning("reddit.health_check failed error=%s", e)
            return {"service": "reddit", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_reddit_scraper_service() -> RedditScraperService:
    return RedditScraperService()


# Module-level alias for backwards compatibility
_svc: RedditScraperService | None = None


def _get() -> RedditScraperService:
    global _svc
    if _svc is None:
        _svc = RedditScraperService()
    return _svc


def fetch_subreddit_signals(
    subreddits: list[str],
    cluster_name: str,
    time_filter: str = "week",
) -> list[dict]:
    return _get().get_subreddit_signals(subreddits, cluster_name, time_filter)
