"""
Pinterest marketing asset generator using Claude Sonnet.
Generates keyword-rich pin titles, descriptions, board suggestions, and variants.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a Pinterest SEO and marketing expert for merchandise brands. "
    "Create keyword-dense, discoverable pins that drive long-term traffic. "
    "Reply with valid JSON only."
)


def generate_pinterest_assets(
    concept_name: str,
    raw_signal: str,
    niche: str,
    shopify_title: str,
    product_types: list[str],
) -> dict:
    """
    Generate Pinterest content package.
    Returns content dict stored in marketing_assets.content.
    """
    products_str = ", ".join(product_types)
    prompt = (
        f"Product: \"{shopify_title}\"\n"
        f"Concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche}\n"
        f"Available as: {products_str}\n\n"
        "Generate Pinterest pin content:\n"
        "- pin_title: Max 100 chars. Keyword-rich, searchable. Include niche keywords.\n"
        "- pin_description: 200-500 chars. Keyword-dense, include gift keywords, "
        "holiday terms if relevant, niche-specific phrases.\n"
        "- board_suggestion: Most relevant Pinterest board name for this niche.\n"
        "- pin_variants: Array of 2-3 alternate pin approaches "
        "(each with title and angle)\n\n"
        "Reply with JSON: {"
        "\"pin_title\": \"...\", \"pin_description\": \"...\", "
        "\"board_suggestion\": \"...\", \"pin_variants\": [{\"title\": ..., \"angle\": ...}]"
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "pinterest_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=768,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        return {
            "pin_title": str(data.get("pin_title", shopify_title))[:100],
            "pin_description": str(data.get("pin_description", ""))[:500],
            "board_suggestion": str(data.get("board_suggestion", niche)),
            "pin_variants": data.get("pin_variants", []),
        }
    except Exception as e:
        logger.error(f"Pinterest generation failed for '{concept_name}': {e}")
        return {
            "pin_title": shopify_title[:100],
            "pin_description": f"Perfect {niche} gift idea. Shop now!",
            "board_suggestion": niche,
            "pin_variants": [],
        }
