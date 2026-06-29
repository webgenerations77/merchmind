from unittest.mock import MagicMock, patch

import pytest

from app.services.intelligence import firecrawl_trends
from app.services.intelligence.firecrawl_trends import FirecrawlTrendsService, _parse_json_array


def _search_payload(titles):
    return {
        "success": True,
        "creditsUsed": 2,
        "data": {
            "web": [
                {"url": f"https://example.com/{i}", "title": t, "description": f"{t} description"}
                for i, t in enumerate(titles)
            ]
        },
    }


@pytest.mark.parametrize("raw,expected", [
    ('["a", "b"]', ["a", "b"]),
    ('```json\n["a", "b"]\n```', ["a", "b"]),
    ('Here you go: ["retro sunset", "mushroom art"] enjoy', ["retro sunset", "mushroom art"]),
    ("not json at all", []),
    ('{"not": "an array"}', []),
])
def test_parse_json_array(raw, expected):
    assert _parse_json_array(raw) == expected


def test_get_trending_merch_signals_returns_standard_shape():
    svc = FirecrawlTrendsService()
    http = MagicMock()
    http.post.return_value = MagicMock(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: _search_payload(["Cottagecore Mushrooms", "80s Synthwave"]),
    )
    svc._client = http

    with patch.object(firecrawl_trends, "settings", MagicMock(FIRECRAWL_API_KEY="fc-test")), \
         patch.object(firecrawl_trends.claude, "haiku",
                      return_value=('["cottagecore mushroom illustration", "retro 80s synthwave sunset"]', None)), \
         patch.object(firecrawl_trends, "_log_usage"):
        signals = svc.get_trending_merch_signals(extra_queries=["trending cat t-shirt designs"])

    assert signals, "expected at least one signal"
    for s in signals:
        assert s["source"] == "firecrawl"
        assert s["raw_signal"]
        assert s["source_metadata"]["type"] == "web_search_concept"
        assert "query" in s["source_metadata"]
    concepts = {s["raw_signal"] for s in signals}
    assert "cottagecore mushroom illustration" in concepts


def test_skips_when_api_key_unset():
    svc = FirecrawlTrendsService()
    with patch.object(firecrawl_trends, "settings", MagicMock(FIRECRAWL_API_KEY="")):
        assert svc.get_trending_merch_signals() == []


def test_search_failure_is_swallowed():
    svc = FirecrawlTrendsService()
    http = MagicMock()
    http.post.side_effect = RuntimeError("network down")
    svc._client = http
    assert svc._search("anything") == []


def test_extract_concepts_filters_garbage():
    svc = FirecrawlTrendsService()
    web = [{"title": "T", "description": "D"}]
    with patch.object(firecrawl_trends.claude, "haiku",
                      return_value=('["x", "a real concept phrase", "ok two"]', None)):
        concepts = svc._extract_concepts("q", web)
    # single-word "x" is rejected (needs >= 2 words)
    assert "x" not in concepts
    assert "a real concept phrase" in concepts


def test_trend_source_enum_includes_firecrawl():
    # The Trend.source Postgres enum must include 'firecrawl', or inserts of
    # firecrawl-sourced trends fail with InvalidTextRepresentation and poison the
    # batch's DB session (root cause of the 2026-06-29 batch wedge).
    from app.models.trend import Trend
    assert "firecrawl" in Trend.__table__.c.source.type.enums


def test_query_count_capped():
    svc = FirecrawlTrendsService()
    calls = []

    def _fake_search(query):
        calls.append(query)
        return []

    with patch.object(firecrawl_trends, "settings", MagicMock(FIRECRAWL_API_KEY="fc-test")), \
         patch.object(svc, "_search", side_effect=_fake_search):
        extra = [f"extra query {i}" for i in range(20)]
        svc.get_trending_merch_signals(extra_queries=extra)

    assert len(calls) <= firecrawl_trends._MAX_QUERIES
