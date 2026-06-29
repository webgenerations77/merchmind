"""
Generates Shopify product copy (title, description, tags) using Claude Sonnet.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)


def sanitize_copy(text: str) -> str:
    """Strip AI-tell punctuation from store copy so it reads like a person wrote it.

    Em-dashes, en-dashes and double-hyphens become a plain comma pause; smart
    quotes/ellipsis become ASCII. Single hyphens (dog-mom, cotton-poly) are kept.
    """
    if not text:
        return text
    text = (text.replace("“", '"').replace("”", '"')   # curly double quotes
                .replace("‘", "'").replace("’", "'")   # curly single quotes
                .replace("…", "..."))                        # ellipsis char
    text = re.sub(r"\s*(?:—|–|--)\s*", ", ", text)       # em/en dash, double hyphen
    text = re.sub(r"\s+,", ",", text)                             # space before comma
    text = re.sub(r",\s*,", ",", text)                           # collapsed double comma
    text = re.sub(r"[ \t]{2,}", " ", text)                       # runs of spaces
    return text.strip()


_SYSTEM = (
    "You write product copy for Spinach The Cow, a quirky print-on-demand brand. "
    "Your voice is casual, dry-witted, and human, never corporate, never cliche. "
    "PUNCTUATION: Use only plain ASCII punctuation. Never use em-dashes or en-dashes "
    "(use a comma, period, or parentheses instead). No smart/curly quotes. This is the "
    "single biggest tell that a robot wrote the copy, so avoid it completely. "
    "You avoid all of the following phrases and AI tells entirely: 'elevate your style', "
    "'perfect for any occasion', 'premium quality', 'make a statement', 'high-quality', "
    "'show your personality', 'express yourself', 'stand out', 'turn heads', 'look no further', "
    "'whether you're', \"it's not just\", \"isn't just\", 'say goodbye to', 'dive into', "
    "'level up', 'game-changer', 'must-have', 'treat yourself', 'one-of-a-kind', 'uniquely you'. "
    "Descriptions are 2-3 sentences max and lead with what makes the specific design interesting, "
    "not generic product praise. Reply with valid JSON only."
)

_PRODUCT_DETAILS = {
    "tshirt": {
        "material": "soft cotton blend",
        "care": "Machine wash cold, tumble dry low",
        "appeal": "A soft cotton tee you'll reach for way too often",
    },
    "hoodie": {
        "material": "heavy blend cotton-polyester fleece",
        "care": "Machine wash cold, tumble dry low, do not iron decoration",
        "appeal": "Heavyweight fleece for cold days and warm opinions",
    },
    "long_sleeve": {
        "material": "soft ringspun cotton, preshrunk",
        "care": "Machine wash cold, tumble dry low",
        "appeal": "Long sleeves for that weird in-between weather",
    },
    "mug": {
        "material": "durable white ceramic, 11oz",
        "care": "Dishwasher and microwave safe",
        "appeal": "Holds 11 ounces of whatever keeps you civil before noon",
    },
    "hat": {
        "material": "structured twill with adjustable snapback",
        "care": "Spot clean only",
        "appeal": "A structured cap that quietly does the talking",
    },
    "phone_case": {
        "material": "impact-resistant polycarbonate with matte finish",
        "care": "Wipe clean with a soft cloth",
        "appeal": "Keeps your phone intact and a little more interesting",
    },
    "sticker": {
        "material": "vinyl, waterproof and UV-resistant",
        "care": "Apply to any clean, smooth surface",
        "appeal": "Slap it on a laptop, bottle, or notebook. It's waterproof, so it survives",
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
        # Sanitizer is the safety net: even if the model slips an em-dash or
        # smart quote past the prompt rules, the stored copy stays clean ASCII.
        title = sanitize_copy(str(data.get("shopify_title", concept_name)))[:60]
        description = sanitize_copy(str(data.get("shopify_description", "")))
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
