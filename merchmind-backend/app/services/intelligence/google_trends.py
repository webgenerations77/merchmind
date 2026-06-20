"""
Google Trends scraper — uses the public RSS feed for daily trending searches
and the pytrends library for rising queries (with graceful fallback).
"""
import logging
import time
import xml.etree.ElementTree as ET
from functools import lru_cache

import httpx

from app.utils.exceptions import GoogleTrendsError

logger = logging.getLogger(__name__)

_RSS_URL = "https://trends.google.com/trending/rss?geo=US"
_PYTRENDS_BACKOFF = [5, 15, 30]


class GoogleTrendsService:
    def __init__(self) -> None:
        self._pytrends_client = None

    def get_trending_searches(self) -> list[dict]:
        """Fetch top trending searches for the US market via RSS feed."""
        results = []
        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(_RSS_URL)
                r.raise_for_status()

            root = ET.fromstring(r.text)
            ns = {"ht": "https://trends.google.com/trending/rss"}

            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                if not title:
                    continue
                traffic = item.findtext("ht:approx_traffic", "", ns).replace("+", "").replace(",", "")
                results.append({
                    "raw_signal": title,
                    "source": "google",
                    "source_metadata": {
                        "type": "trending_search",
                        "market": "US",
                        "approx_traffic": traffic,
                    },
                })

            logger.info("google_trends.trending_searches count=%d", len(results))
        except Exception as e:
            logger.error("google_trends.trending_searches failed error=%s", e)
            raise GoogleTrendsError(f"trending_searches failed: {e}") from e
        return results

    def get_rising_queries(self, keywords: list[str], cluster_name: str) -> list[dict]:
        """Fetch rising queries for a niche cluster's keywords. Uses pytrends with fallback."""
        results = []
        try:
            from pytrends.request import TrendReq
            if self._pytrends_client is None:
                self._pytrends_client = TrendReq(hl="en-US", tz=360, timeout=(30, 30))
            pt = self._pytrends_client
        except Exception as e:
            logger.warning("google_trends.rising_queries pytrends unavailable: %s", e)
            return results

        batches = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]

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

    def health_check(self) -> dict:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(_RSS_URL)
                ok = r.status_code == 200 and "<item>" in r.text
            return {"service": "google_trends", "ok": ok}
        except Exception as e:
            logger.warning("google_trends.health_check failed error=%s", e)
            return {"service": "google_trends", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_google_trends_service() -> GoogleTrendsService:
    return GoogleTrendsService()


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
