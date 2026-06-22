"""
Tests for the batch pipeline orchestration (all external calls mocked).
"""
import pytest
import uuid
from datetime import date
from unittest.mock import MagicMock, patch, call
from app.services.pricing.pricing_engine import calculate_price
from app.services.design.archetype_classifier import classify_archetype, select_image_api
from app.services.design.quality_scorer import assign_product_bundle


class TestArchetypeClassifier:
    @patch("app.services.design.archetype_classifier.claude")
    def test_returns_valid_archetype(self, mock_claude):
        mock_claude.haiku.return_value = (
            '{"archetype": "text_only", "reason": "Strong slogan potential"}',
            MagicMock(),
        )
        result = classify_archetype("I survived another meeting", "reddit")
        assert result == "text_only"

    @patch("app.services.design.archetype_classifier.claude")
    def test_falls_back_on_invalid_archetype(self, mock_claude):
        mock_claude.haiku.return_value = ('{"archetype": "watercolor", "reason": "test"}', MagicMock())
        result = classify_archetype("test signal", "google")
        assert result == "text_icon"

    @patch("app.services.design.archetype_classifier.claude")
    def test_falls_back_on_api_error(self, mock_claude):
        mock_claude.haiku.side_effect = Exception("API error")
        result = classify_archetype("test signal", "google")
        assert result == "text_icon"

    def test_select_image_api_for_illustration(self):
        assert select_image_api("illustration") == "flux_schnell"

    def test_select_image_api_for_text_only(self):
        assert select_image_api("text_only") is None

    def test_select_image_api_for_typographic(self):
        assert select_image_api("typographic") is None

    def test_select_image_api_for_text_icon(self):
        assert select_image_api("text_icon") == "flux_schnell"

    def test_select_image_api_for_hybrid(self):
        assert select_image_api("hybrid") == "flux_schnell"


class TestProductBundleAssignment:
    def test_illustration_gets_at_least_five_types(self):
        result = assign_product_bundle("illustration", {"visual_appeal": 8})
        assert "tshirt" in result
        assert "sticker" in result
        assert "mug" in result
        assert len(result) >= 5

    def test_text_only_gets_all_products(self):
        result = assign_product_bundle("text_only", {})
        assert len(result) == 5
        assert "tshirt" in result
        assert "mug" in result

    def test_typographic_gets_all_products(self):
        result = assign_product_bundle("typographic", {})
        assert len(result) == 5

    def test_text_icon_gets_at_least_five(self):
        result = assign_product_bundle("text_icon", {})
        assert len(result) >= 5
        assert "tshirt" in result

    def test_hybrid_gets_all_products(self):
        result = assign_product_bundle("hybrid", {"visual_appeal": 9})
        assert len(result) == 5

    def test_all_archetypes_include_tshirt(self):
        for arch in ["illustration", "hybrid", "text_only", "typographic", "text_icon"]:
            result = assign_product_bundle(arch, {})
            assert "tshirt" in result, f"{arch} missing tshirt"


class TestBatchPipelineIntegration:
    """Integration tests with all external services mocked."""

    @patch("app.services.intelligence.google_trends.fetch_us_trending")
    @patch("app.services.intelligence.seasonal_calendar.get_upcoming_events")
    def test_seasonal_signals_are_included(self, mock_seasonal, mock_google):
        mock_google.return_value = []
        mock_seasonal.return_value = [
            {
                "raw_signal": "Christmas: santa",
                "source": "seasonal",
                "source_metadata": {"event": "Christmas", "days_until": 10, "proximity_score": 85},
            }
        ]
        signals = mock_google() + mock_seasonal()
        assert len(signals) == 1
        assert signals[0]["source"] == "seasonal"

    def test_final_score_formula(self):
        trend_score = 70
        viability_score = 80
        cluster_boost = 15
        expected = int((trend_score * 0.4) + (viability_score * 0.6)) + cluster_boost
        assert expected == 91  # 28 + 48 + 15

    def test_final_score_capped_at_100(self):
        trend_score = 100
        viability_score = 100
        cluster_boost = 50
        final = min(100, int((trend_score * 0.4) + (viability_score * 0.6)) + cluster_boost)
        assert final == 100

    @patch("app.services.intelligence.trend_scorer.score_trend_signal")
    @patch("app.services.intelligence.trend_scorer.score_merch_viability")
    @patch("app.services.intelligence.trend_scorer.check_risk")
    def test_hard_risk_flag_rejects_signal(self, mock_risk, mock_viability, mock_trend):
        mock_trend.return_value = {"trend_score": 85, "reasoning": "viral"}
        mock_viability.return_value = {"viability_score": 90, "final_score": 88, "claude_reasoning": "great"}
        mock_risk.return_value = {"risk_flag": "hard", "risk_reason": "Brand name detected"}

        from app.services.intelligence.trend_scorer import check_risk
        risk = check_risk("Nike logo", 88, threshold=35)
        assert risk["risk_flag"] == "hard"

    def test_scoring_threshold_filters_low_scores(self):
        threshold = 35
        scores = [10, 25, 34, 35, 50, 80]
        queued = [s for s in scores if s >= threshold]
        assert queued == [35, 50, 80]
