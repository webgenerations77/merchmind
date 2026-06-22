"""
Pricing engine: calculates retail price from Printify base cost,
markup settings, trend-based adjustment, and enforces floor prices.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

_MARGIN_WARNING_THRESHOLD = Decimal("0.30")  # 30%

DEFAULT_BASE_MARKUP = {
    "tshirt": Decimal("2.5"),
    "mug": Decimal("2.8"),
    "hat": Decimal("2.5"),
    "phone_case": Decimal("2.5"),
    "sticker": Decimal("3.0"),
}

DEFAULT_FLOOR_PRICES = {
    "tshirt": Decimal("24.99"),
    "mug": Decimal("18.99"),
    "hat": Decimal("26.99"),
    "phone_case": Decimal("22.99"),
    "sticker": Decimal("6.99"),
}


def calculate_price(
    product_type: str,
    printify_base_cost: float,
    final_score: int,
    base_markup: dict | None = None,
    floor_prices: dict | None = None,
    trend_boost_max: float = 0.20,
) -> dict:
    """
    Calculate retail price for a product.

    Formula:
        base_price = printify_base_cost × markup_factor
        trend_adjustment = (final_score / 100) × trend_boost_max × base_price
        retail_price = base_price + trend_adjustment
        retail_price = max(retail_price, floor_price)

    Returns dict with pricing breakdown and margin_flag.
    """
    markup_map = {k: Decimal(str(v)) for k, v in (base_markup or DEFAULT_BASE_MARKUP).items()}
    floor_map = {k: Decimal(str(v)) for k, v in (floor_prices or DEFAULT_FLOOR_PRICES).items()}

    if product_type not in markup_map:
        raise ValueError(f"Unknown product type for pricing: '{product_type}'")

    base_cost = Decimal(str(printify_base_cost))
    markup = markup_map[product_type]
    floor = floor_map[product_type]
    boost_max = Decimal(str(trend_boost_max))
    score = Decimal(str(max(0, min(100, final_score))))

    base_price = (base_cost * markup).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    trend_adj = ((score / 100) * boost_max * base_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    retail = base_price + trend_adj

    # Enforce floor price
    retail = max(retail, floor)

    # Calculate margin
    margin = (retail - base_cost) / retail if retail > 0 else Decimal("0")
    margin_flag = margin < _MARGIN_WARNING_THRESHOLD

    if margin_flag:
        logger.warning(
            f"Margin warning: {product_type} margin={float(margin):.1%} "
            f"(cost={base_cost}, retail={retail})"
        )

    return {
        "printify_base_cost": float(base_cost),
        "base_markup": float(markup),
        "trend_adjustment": float(trend_adj),
        "retail_price": float(retail),
        "floor_price": float(floor),
        "margin": float(margin),
        "margin_flag": margin_flag,
    }


def price_product_bundle(
    product_types: list[str],
    printify_base_costs: dict[str, float],
    final_score: int,
    base_markup: dict | None = None,
    floor_prices: dict | None = None,
    trend_boost_max: float = 0.20,
) -> dict[str, dict]:
    """
    Price an entire product bundle.
    printify_base_costs: {product_type: cost} dict.
    Returns {product_type: pricing_dict} for each type.
    """
    results = {}
    for pt in product_types:
        cost = printify_base_costs.get(pt, 0.0)
        if cost <= 0:
            logger.warning(f"No base cost for {pt}, using 0 — pricing will be at floor")
        results[pt] = calculate_price(
            pt, cost, final_score, base_markup, floor_prices, trend_boost_max
        )
    return results
