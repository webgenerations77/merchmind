"""
Blog post generator using Claude Sonnet.
Creates niche-content articles that naturally feature the product (not product descriptions).
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a content marketing writer specializing in niche communities. "
    "Write authentic, helpful articles that naturally feature merchandise without feeling like ads. "
    "Reply with valid JSON only."
)


def generate_blog_post(
    concept_name: str,
    raw_signal: str,
    niche: str,
    shopify_title: str,
    product_types: list[str],
) -> dict:
    """
    Generate a blog post asset.
    Returns content dict stored in marketing_assets.content.
    """
    products_str = ", ".join(product_types)
    prompt = (
        f"Product to naturally feature: \"{shopify_title}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche community: {niche}\n"
        f"Available as: {products_str}\n\n"
        "Write a blog post that provides genuine value to the niche community "
        "and naturally mentions the product — NOT a product description:\n"
        "- title: SEO-optimized, niche-relevant, compelling\n"
        "- body: 300-500 word article. Write for the niche community first. "
        "Mention the product naturally as a recommendation or example, "
        "not as the main focus. Use H2 subheadings.\n"
        "- meta_title: 60 chars max, SEO-optimized\n"
        "- meta_description: 155 chars max, includes primary keyword\n\n"
        "Reply with JSON: {"
        "\"title\": \"...\", \"body\": \"...\", "
        "\"meta_title\": \"...\", \"meta_description\": \"...\""
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "blog_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=2048,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        return {
            "title": str(data.get("title", f"The {niche} Community's Latest Obsession")),
            "body": str(data.get("body", "")),
            "meta_title": str(data.get("meta_title", shopify_title))[:60],
            "meta_description": str(data.get("meta_description", ""))[:155],
        }
    except Exception as e:
        logger.error(f"Blog generation failed for '{concept_name}': {e}")
        return {
            "title": f"Why {niche} Fans Are Loving This New Design",
            "body": f"<p>The {niche} community has been buzzing about {raw_signal}...</p>",
            "meta_title": shopify_title[:60],
            "meta_description": f"Discover {niche} merchandise for every fan.",
        }
