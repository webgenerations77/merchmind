"""
Generates Shopify product copy (title, description, tags) using Claude Sonnet.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You write product copy for Spinach The Cow, a quirky print-on-demand brand. "
    "Your voice is casual, dry-witted, and human — never corporate, never cliché. "
    "You avoid all of the following phrases entirely: 'elevate your style', "
    "'perfect for any occasion', 'premium quality', 'make a statement', "
    "'high-quality', 'show your personality', 'express yourself', 'stand out'. "
    "Descriptions are 2-3 sentences max and lead with what makes the specific design interesting, "
    "not generic product praise. Reply with valid JSON only."
)

_PRODUCT_DETAILS = {
    "tshirt": {
        "material": "premium cotton blend",
        "care": "Machine wash cold, tumble dry low",
        "appeal": "Comfortable everyday wear with a design that speaks for itself",
    },
    "hoodie": {
        "material": "heavy blend cotton-polyester fleece",
        "care": "Machine wash cold, tumble dry low, do not iron decoration",
        "appeal": "Stay cozy and stylish with a hoodie that makes a statement",
    },
    "long_sleeve": {
        "material": "soft ringspun cotton, preshrunk",
        "care": "Machine wash cold, tumble dry low",
        "appeal": "Layer up with a long sleeve that brings your personality to every season",
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
    # Example of the tone we want:
    # Design: "Feral Raccoon Energy" → "This one's for everyone who relates to a trash panda
    # running on spite and black coffee. Soft tee, chaotic energy, zero apologies."
    prompt = (
        f"Design concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Archetype: {archetype}\n"
        f"Product types: {products_str}\n\n"
        "Write Shopify copy in our brand voice — casual, dry, human. "
        "Lead with what's interesting about THIS specific design, not generic product praise.\n\n"
        "- shopify_title: Max 60 chars. Clear and searchable. Skip the fluff.\n"
        "- shopify_description: 2-3 sentences only. "
        "Start with what makes this design click with someone, not what the product is made of. "
        "No banned phrases. Sound like a person wrote it on a Tuesday afternoon.\n"
        "- shopify_tags: Array of 20-30 tags covering niche, mood, occasion, product type, gifting.\n\n"
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
