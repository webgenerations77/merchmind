"""
Generates Shopify product copy (title, description, tags) using Claude Sonnet.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an expert Shopify product copywriter specializing in "
    "print-on-demand merchandise. Write SEO-optimized, conversion-focused copy. "
    "Reply with valid JSON only."
)

_PRODUCT_DETAILS = {
    "tshirt": {
        "material": "premium cotton blend",
        "care": "Machine wash cold, tumble dry low",
        "appeal": "Comfortable everyday wear with a design that speaks for itself",
    },
    "mug": {
        "material": "durable white ceramic, 11oz",
        "care": "Dishwasher and microwave safe",
        "appeal": "Start your morning right with art that sets the tone for your day",
    },
    "hat": {
        "material": "structured twill with adjustable snapback",
        "care": "Spot clean only",
        "appeal": "Top off any outfit with a design that turns heads",
    },
    "phone_case": {
        "material": "impact-resistant polycarbonate with matte finish",
        "care": "Wipe clean with a soft cloth",
        "appeal": "Protect your phone in style with a case that's uniquely you",
    },
    "sticker": {
        "material": "premium vinyl, waterproof and UV-resistant",
        "care": "Apply to any clean, smooth surface",
        "appeal": "Stick it anywhere — laptops, water bottles, notebooks, you name it",
    },
}


def generate_shopify_copy(
    concept_name: str,
    raw_signal: str,
    archetype: str,
    product_types: list[str],
    niche: str = "",
) -> dict:
    """
    Generate Shopify title, description, and tags for a design.
    Returns {shopify_title: str, shopify_description: str, shopify_tags: list[str]}.
    """
    products_str = ", ".join(product_types)
    prompt = (
        f"Design concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Archetype: {archetype}\n"
        f"Product types: {products_str}\n\n"
        "Generate Shopify product listing copy:\n"
        "- shopify_title: Max 60 chars. Keyword-rich. Include main niche keyword.\n"
        "- shopify_description: 150-300 words. SEO-optimized. "
        "Start with a hook, describe the design appeal, mention product quality, "
        "include a CTA. Use niche-specific language.\n"
        "- shopify_tags: Array of 20-30 tags. Mix: niche keywords, product type, "
        "occasion, style, gifting terms.\n\n"
        "Reply with JSON: {"
        "\"shopify_title\": \"...\", "
        "\"shopify_description\": \"...\", "
        "\"shopify_tags\": [\"...\", ...]"
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "shopify_copy",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=1024,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        title = str(data.get("shopify_title", concept_name))[:60]
        description = str(data.get("shopify_description", ""))
        tags = data.get("shopify_tags", [])
        if not isinstance(tags, list):
            tags = []
        return {
            "shopify_title": title,
            "shopify_description": description,
            "shopify_tags": tags[:30],
        }
    except Exception as e:
        logger.error(f"Shopify copy generation failed for '{concept_name}': {e}")
        return {
            "shopify_title": concept_name[:60],
            "shopify_description": f"A unique {niche or 'merchandise'} design.",
            "shopify_tags": [raw_signal, niche or "merch", archetype],
        }


def get_product_description(
    base_description: str,
    product_type: str,
    concept_name: str,
) -> str:
    """
    Adapt the base shopify description for a specific product type.
    Prepends product-specific intro and appends material/care details.
    """
    details = _PRODUCT_DETAILS.get(product_type)
    if not details:
        return base_description

    product_label = product_type.replace("_", " ").title()
    intro = f"{details['appeal']}.\n\n"
    outro = (
        f"\n\nProduct Details:\n"
        f"- Material: {details['material']}\n"
        f"- Care: {details['care']}\n"
    )
    return f"{intro}{base_description}{outro}"
