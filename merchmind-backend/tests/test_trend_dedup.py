from unittest.mock import MagicMock

import pytest

from app.services.intelligence.trend_dedup import normalize_concept, build_seen_set


@pytest.mark.parametrize("raw,expected", [
    ("Coffee Lovers: But First Coffee!", "coffee lovers but first coffee"),
    ("  Dog Lovers — Dog Mom  ", "dog lovers dog mom"),
    ("HELLO", "hello"),
    ("", ""),
    (None, ""),
])
def test_normalize_concept(raw, expected):
    assert normalize_concept(raw) == expected


def test_punctuation_and_case_variants_normalize_equal():
    assert normalize_concept("but first, COFFEE!") == normalize_concept("But First Coffee")


def test_build_seen_set_includes_designs_and_recent_trends():
    db = MagicMock()
    # build_seen_set makes two queries: designs first, then recent trends.
    db.query.return_value.filter.return_value.all.side_effect = [
        [("Coffee Lovers: But First Coffee!",)],   # Design.concept_name rows
        [("Dog Lovers — Dog Mom",)],               # Trend.raw_signal rows
    ]
    seen = build_seen_set(db, weeks=8)
    assert "coffee lovers but first coffee" in seen
    assert "dog lovers dog mom" in seen


def test_build_seen_set_skips_empty_values():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [
        [(None,)],   # design with null concept
        [("",)],     # trend with empty signal
    ]
    assert build_seen_set(db) == set()
