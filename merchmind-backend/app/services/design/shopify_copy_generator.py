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
