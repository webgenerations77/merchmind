"""
Google Trends scraper — class-based wrapper around pytrends.
Fetches US trending searches and rising queries for niche cluster keywords.
"""
import logging
import time
from functools import lru_cache
from pytrends.request import TrendReq

from app.utils.exceptions import GoogleTrendsError

logger = logging.getLogger(__name__)

_PYTRENDS_BACKOFF = [5, 15, 30]


class GoogleTrendsService:
    def __init__(self) -> None:
        self._client: TrendReq | None = None

    def _get_client(self) -> TrendReq:
        if self._client is None:
            self._client = TrendReq(hl="en-US", tz=360, timeout=(30, 30), retries=3, backoff_factor=0.5)
        return self._client

    def get_trending_searches(self) -> list[dict]:
        """Fetch top trending searches for the US market."""
        results = []
        try:
            pt = self._get_client()
            trending_df = pt.trending_searches(pn="united_states")
            for term in trending_df[0].tolist():
                results.append({
                    "raw_signal": term,
                    "source": "google",
                    "source_metadata": {"type": "trending_search", "market": "US"},
                })
            logger.info("google_trends.trending_searches count=%d", len(results))
        except Exception as e:
            logger.error("google_trends.trending_searches failed error=%s", e)
            raise GoogleTrendsError(f"trending_searches failed: {e}") from e
        return results

    def get_rising_queries(self, keywords: list[str], cluster_name: str) -> list[dict]:
        """Fetch rising queries for a niche cluster's keywords (max 5 per pytrends request)."""
        results = []
        batches = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]
        pt = self._get_client()

        for batch in batches:
            for attempt, backoff in enumerate([0] + _PYTRENDS_BACKOFF):
                if backoff:
                    time.sleep(backoff)
                try:
                    pt.build_payload(batch, timeframe="now 7-d", geo="US")
                    related = pt.related_queries()
                    for kw in batch:
                        rising_df = related.get(kw, {}).get("rising")
                        if rising_df is not None and not rising_df.empty:
                            for _, row in rising_df.iterrows():
                                results.append({
                                    "raw_signal": row["query"],
                                    "source": "google",
                                    "source_metadata": {
                                        "type": "rising_query",
                                        "seed_keyword": kw,
                                        "cluster": cluster_name,
                                        "value": int(row.get("value", 0)),
                                    },
                                })
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < len(_PYTRENDS_BACKOFF):
                        logger.warning("google_trends.rising_queries 429 batch=%s retry=%d", batch, attempt + 1)
                        continue
                    logger.error("google_trends.rising_queries failed batch=%s error=%s", batch, e)
                    break

        logger.info("google_trends.rising_queries cluster=%s count=%d", cluster_name, len(results))
        return results

    def get_interest_over_time(self, keywords: list[str], timeframe: str = "today 3-m") -> dict:
        """Return interest-over-time data for up to 5 keywords."""
        try:
            pt = self._get_client()
            pt.build_payload(keywords[:5], timeframe=timeframe, geo="US")
            df = pt.interest_over_time()
            if df.empty:
                return {}
            result = {}
            for kw in keywords[:5]:
                if kw in df.columns:
                    result[kw] = df[kw].tolist()
            logger.info("google_trends.interest_over_time keywords=%s", keywords[:5])
            return result
        except Exception as e:
            logger.error("google_trends.interest_over_time failed error=%s", e)
            raise GoogleTrendsError(f"interest_over_time failed: {e}") from e

    def calculate_trajectory(self, keyword: str) -> float:
        """
        Return a trajectory score in [-1.0, 1.0].
        Positive = trending up, negative = trending down.
        Uses 4-week vs prior average comparison.
        """
        try:
            data = self.get_interest_over_time([keyword], timeframe="today 3-m")
            series = data.get(keyword, [])
            if len(series) < 8:
                return 0.0
            recent = sum(series[-4:]) / 4
            baseline = sum(series[:-4]) / len(series[:-4])
            if baseline == 0:
                return 0.0
            change = (recent - baseline) / baseline
            return max(-1.0, min(1.0, change))
        except GoogleTrendsError:
            return 0.0

    def health_check(self) -> dict:
        try:
            pt = self._get_client()
            df = pt.trending_searches(pn="united_states")
            ok = not df.empty
            return {"service": "google_trends", "ok": ok}
        except Exception as e:
            logger.warning("google_trends.health_check failed error=%s", e)
            return {"service": "google_trends", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_google_trends_service() -> GoogleTrendsService:
    return GoogleTrendsService()


# Module-level aliases for backwards compatibility with existing pipeline code
_svc: GoogleTrendsService | None = None


def _get() -> GoogleTrendsService:
    global _svc
    if _svc is None:
        _svc = GoogleTrendsService()
    return _svc


def fetch_us_trending() -> list[dict]:
    return _get().get_trending_searches()


def fetch_rising_queries(keywords: list[str], cluster_name: str) -> list[dict]:
    return _get().get_rising_queries(keywords, cluster_name)
