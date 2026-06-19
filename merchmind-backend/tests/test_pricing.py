"""
Tests for the pricing engine.
"""
import pytest
from decimal import Decimal
from app.services.pricing.pricing_engine import calculate_price, price_product_bundle


class TestCalculatePrice:
    def test_basic_tshirt_pricing(self):
        result = calculate_price("tshirt", 8.50, 50)
        assert result["retail_price"] >= 24.99  # floor enforced
        assert result["printify_base_cost"] == 8.50
        assert result["base_markup"] == 2.5

    def test_floor_price_enforced(self):
        # Very low base cost should still hit floor
        result = calculate_price("sticker", 1.00, 0)
        assert result["retail_price"] >= 6.99

    def test_trend_adjustment_increases_price(self):
        result_low = calculate_price("tshirt", 10.00, 0)
        result_high = calculate_price("tshirt", 10.00, 100)
        assert result_high["retail_price"] >= result_low["retail_price"]

    def test_trend_adjustment_max(self):
        result = calculate_price("tshirt", 10.00, 100, trend_boost_max=0.20)
        base_price = 10.00 * 2.5  # 25.00
        max_trend_adj = 1.0 * 0.20 * base_price  # 5.00
        # retail should be base + trend_adj = 30.00, but floor is 24.99 so 30.00
        assert abs(result["retail_price"] - (base_price + max_trend_adj)) < 0.02

    def test_margin_flag_below_threshold(self):
        # Base cost = 20, markup 1.1 → retail = 22, margin = 2/22 ≈ 9%
        result = calculate_price(
            "tshirt", 20.00, 0,
            base_markup={"tshirt": 1.1},
            floor_prices={"tshirt": 0.01},  # disable floor for test
        )
        assert result["margin_flag"] is True

    def test_margin_flag_above_threshold(self):
        result = calculate_price("tshirt", 8.50, 50)
        # margin = (retail - 8.50) / retail, should be > 30%
        margin = (result["retail_price"] - 8.50) / result["retail_price"]
        if margin >= 0.30:
            assert result["margin_flag"] is False

    def test_invalid_product_type_raises(self):
        with pytest.raises(ValueError, match="Unknown product type"):
            calculate_price("jetpack", 10.00, 50)

    def test_all_product_types(self):
        types = ["tshirt", "mug", "hat", "phone_case", "sticker", "poster"]
        costs = {"tshirt": 8.50, "mug": 5.00, "hat": 9.00, "phone_case": 7.00, "sticker": 2.00, "poster": 11.00}
        for pt in types:
            result = calculate_price(pt, costs[pt], 60)
            assert result["retail_price"] > 0

    def test_price_bundle(self):
        bundle = price_product_bundle(
            ["tshirt", "mug"],
            {"tshirt": 8.50, "mug": 5.00},
            final_score=65,
        )
        assert "tshirt" in bundle
        assert "mug" in bundle
        assert bundle["tshirt"]["retail_price"] >= 24.99
        assert bundle["mug"]["retail_price"] >= 18.99
