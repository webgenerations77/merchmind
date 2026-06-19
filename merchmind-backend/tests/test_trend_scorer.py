"""
Tests for the trend scoring pipeline.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from app.services.intelligence.trend_scorer import (
    score_trend_signal,
    score_merch_viability,
    check_risk,
    _extract_json,
)


class TestExtractJson:
    def test_extracts_simple_json(self):
        text = 'Here is the result: {"score": 75, "reason": "good"}'
        result = _extract_json(text)
        assert json.loads(result) == {"score": 75, "reason": "good"}

    def test_raises_when_no_json(self):
        with pytest.raises(ValueError, match="No JSON found"):
            _extract_json("No JSON here at all")

    def test_extracts_nested_json(self):
        text = '{"outer": {"inner": 42}}'
        result = _extract_json(text)
        data = json.loads(result)
        assert data["outer"]["inner"] == 42


class TestScoreTrendSignal:
    @patch("app.services.intelligence.trend_scorer.claude")
    def test_returns_valid_score(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"trend_score": 75, "reasoning": "Rising fast across platforms"}',
            MagicMock(),
        )
        result = score_trend_signal("dog mom life", "reddit", {"score": 2500})
        assert result["trend_score"] == 75
        assert "reasoning" in result

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_clamps_score_to_100(self, mock_claude):
        mock_claude.haiku.return_value = ('{"trend_score": 150, "reasoning": "too high"}', MagicMock())
        result = score_trend_signal("test", "google", {})
        assert result["trend_score"] == 100

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_clamps_score_to_0(self, mock_claude):
        mock_claude.haiku.return_value = ('{"trend_score": -10, "reasoning": "negative"}', MagicMock())
        result = score_trend_signal("test", "google", {})
        assert result["trend_score"] == 0

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_handles_api_failure_gracefully(self, mock_claude):
        mock_claude.haiku.side_effect = Exception("API down")
        result = score_trend_signal("test", "google", {})
        assert result["trend_score"] == 0
        assert "Scoring failed" in result["reasoning"]


class TestScoreMerchViability:
    @patch("app.services.intelligence.trend_scorer.claude")
    def test_calculates_final_score(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"viability_score": 80, "breakdown": {}, "claude_reasoning": "Strong niche appeal"}',
            MagicMock(),
        )
        result = score_merch_viability("dog mom", 70)
        # final = (70 * 0.4) + (80 * 0.6) = 28 + 48 = 76
        assert result["final_score"] == 76
        assert result["viability_score"] == 80

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_applies_cluster_boost(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"viability_score": 60, "breakdown": {}, "claude_reasoning": "OK"}',
            MagicMock(),
        )
        result_no_boost = score_merch_viability("dog mom", 60, cluster_boost=0)
        result_with_boost = score_merch_viability("dog mom", 60, cluster_boost=15)
        assert result_with_boost["final_score"] == result_no_boost["final_score"] + 15

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_final_score_capped_at_100(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"viability_score": 100, "breakdown": {}, "claude_reasoning": "Perfect"}',
            MagicMock(),
        )
        result = score_merch_viability("test", 100, cluster_boost=50)
        assert result["final_score"] <= 100


class TestCheckRisk:
    def test_skips_check_below_threshold(self):
        result = check_risk("anything", score=20, threshold=35)
        assert result["risk_flag"] == "none"
        assert result["risk_reason"] is None

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_detects_hard_flag(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"risk_flag": "hard", "risk_reason": "Brand name detected"}',
            MagicMock(),
        )
        result = check_risk("Nike just do it", score=80, threshold=35)
        assert result["risk_flag"] == "hard"
        assert result["risk_reason"] == "Brand name detected"

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_detects_none_flag(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"risk_flag": "none", "risk_reason": null}',
            MagicMock(),
        )
        result = check_risk("dog mom life", score=80, threshold=35)
        assert result["risk_flag"] == "none"

    @patch("app.services.intelligence.trend_scorer.claude")
    def test_handles_invalid_flag_value(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"risk_flag": "maybe", "risk_reason": "unclear"}',
            MagicMock(),
        )
        result = check_risk("test topic", score=80)
        assert result["risk_flag"] == "none"  # invalid values default to none
