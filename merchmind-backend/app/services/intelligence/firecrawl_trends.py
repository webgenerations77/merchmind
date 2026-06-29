"""
Firecrawl trend source — pulls trending print-on-demand / merch signals from the
open web via Firecrawl's `/search` endpoint, then distills each result into
concrete merch concept phrases with Claude Haiku.

This AUGMENTS the existing trend sources (google_trends, reddit, twitter,
seasonal). It returns the same `{raw_signal, source, source_url,
source_metadata}` shape so downstream scoring + cross-batch dedup are unchanged.

Why it exists: the scrape path repeatedly yielded ~0 queued trends because the
8-week cross-batch dedup absorbs anything close to the existing catalog and
pytrends rate-limit hangs starve the batch. Firecrawl search broadens raw
variety from marketplace-bestseller / trending-merch articles.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import httpx

from app.config import settings
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
_RESULTS_PER_QUERY = 6
_CONCEPTS_PER_QUERY = 4
_MAX_QUERIES = 8       # bound credit + Claude spend and keep wall time under the batch's 60s scraper timeout
_MAX_WORKERS = 4       # search+extract run concurrently so total runtime stays well below the timeout
# Firecrawl Standard plan ≈ $0.00083 / credit (search ≈ 2 credits/result page).
_COST_PER_CREDIT = 0.00083

# Curated queries that surface fresh, concrete merch subject matter rather than
# generic "design trends" listicles. Kept short to bound credit + Claude spend.
_DEFAULT_QUERIES = [
    "best selling t-shirt designs this week Etsy",
    "trending print on demand niches right now",
    "viral graphic tee ideas this month",
    "Redbubble trending sticker and shirt themes",
    "what merch is selling this season pop culture",
]


class FirecrawlTrendsService:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=30,
                headers={
                    "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _search(self, query: str) -> list[dict]:
        """Run one Firecrawl web search. Returns the raw `data.web` list (may be empty)."""
        try:
            r = self._http().post(
                _SEARCH_URL,
                json={"query": query, "limit": _RESULTS_PER_QUERY, "sources": ["web"]},
            )
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            logger.warning("firecrawl.search failed query=%r error=%s", query, e)
            return []

        if not payload.get("success"):
            logger.warning("firecrawl.search not-success query=%r payload=%s", query, str(payload)[:200])
            return []

        _log_usage("search", payload.get("creditsUsed", 0))
        web = (payload.get("data") or {}).get("web") or []
        logger.info("firecrawl.search query=%r results=%d", query, len(web))
        return web

    def _extract_concepts(self, query: str, web_results: list[dict]) -> list[str]:
        """Distill search-result titles/descriptions into concrete merch concept phrases."""
        snippets = "\n".join(
            f"- {(w.get('title') or '').strip()}: {(w.get('description') or '').strip()}"
            for w in web_results
            if w.get("title") or w.get("description")
        )
        if not snippets.strip():
            return []

        prompt = (
            f"These web search results describe trending print-on-demand / merch themes "
            f"(search: \"{query}\"):\n\n{snippets}\n\n"
            f"Extract up to {_CONCEPTS_PER_QUERY} CONCRETE, specific design concepts that could "
            "each become a single graphic t-shirt or sticker. Each must be a 2-6 word concrete "
            "subject (e.g. \"cottagecore mushroom illustration\", \"retro 80s sunset synthwave\"), "
            "NOT a generic marketing phrase. Reject vague words like 'trends', 'designs', "
            "'popular', 'best sellers', '2026', 'ideas'. "
            'Reply with ONLY a JSON array of strings, e.g. ["concept one", "concept two"].'
        )
        try:
            text, _ = claude.haiku(
                "firecrawl_concept_extraction",
                [{"role": "user", "content": prompt}],
                max_tokens=256,
            )
            concepts = _parse_json_array(text)
        except Exception as e:
            logger.warning("firecrawl.extract_concepts failed query=%r error=%s", query, e)
            return []

        cleaned = []
        for c in concepts:
            c = str(c).strip().strip('"').strip()
            if 2 <= len(c.split()) <= 8 and len(c) >= 3:
                cleaned.append(c)
        return cleaned[:_CONCEPTS_PER_QUERY]

    def get_trending_merch_signals(self, extra_queries: list[str] | None = None) -> list[dict]:
        """
        Search curated (+ optional niche-derived) queries and return merch concept signals.
        Returns list of {raw_signal, source, source_url, source_metadata} dicts.
        """
        if not settings.FIRECRAWL_API_KEY:
            logger.warning("firecrawl.get_trending_merch_signals skipped — FIRECRAWL_API_KEY unset")
            return []

        queries = list(dict.fromkeys(_DEFAULT_QUERIES + (extra_queries or [])))[:_MAX_QUERIES]

        def _one(query: str) -> list[dict]:
            web = self._search(query)
            if not web:
                return []
            top_url = web[0].get("url")
            return [{
                "raw_signal": concept,
                "source": "firecrawl",
                "source_url": top_url,
                "source_metadata": {
                    "type": "web_search_concept",
                    "query": query,
                    "result_count": len(web),
                },
            } for concept in self._extract_concepts(query, web)]

        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
            for chunk in ex.map(_one, queries):
                results.extend(chunk)

        logger.info("firecrawl.get_trending_merch_signals queries=%d signals=%d", len(queries), len(results))
        return results

    def health_check(self) -> dict:
        if not settings.FIRECRAWL_API_KEY:
            return {"service": "firecrawl", "ok": False, "error": "FIRECRAWL_API_KEY unset"}
        try:
            r = self._http().post(_SEARCH_URL, json={"query": "test", "limit": 1, "sources": ["web"]})
            ok = r.status_code == 200 and bool(r.json().get("success"))
            return {"service": "firecrawl", "ok": ok}
        except Exception as e:
            logger.warning("firecrawl.health_check failed error=%s", e)
            return {"service": "firecrawl", "ok": False, "error": str(e)}


def _parse_json_array(text: str) -> list:
    """Best-effort parse of a JSON array, tolerating code fences / surrounding prose."""
    text = text.strip()
    if "[" in text and "]" in text:
        text = text[text.index("["): text.rindex("]") + 1]
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _log_usage(operation: str, credits: int) -> None:
    """Fire-and-forget ApiUsageLog entry so the dashboard Usage page tracks Firecrawl spend."""
    try:
        from app.database import SessionLocal
        from app.models.api_usage_log import ApiUsageLog
        db = SessionLocal()
        db.add(ApiUsageLog(
            service="firecrawl",
            operation=operation,
            model="search",
            estimated_cost=round(credits * _COST_PER_CREDIT, 6),
        ))
        db.commit()
        db.close()
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_firecrawl_trends_service() -> FirecrawlTrendsService:
    return FirecrawlTrendsService()


_svc: FirecrawlTrendsService | None = None


def _get() -> FirecrawlTrendsService:
    global _svc
    if _svc is None:
        _svc = FirecrawlTrendsService()
    return _svc


def fetch_trending_merch(extra_queries: list[str] | None = None) -> list[dict]:
    return _get().get_trending_merch_signals(extra_queries)
