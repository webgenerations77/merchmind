"""
Instagram marketing asset generator using Claude Sonnet.
Generates post style selection, caption, hashtags, and story variant.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an expert Instagram marketing strategist for merchandise brands. "
    "Create engaging, niche-specific content that drives purchases. "
    "Reply with valid JSON only."
)


def generate_instagram_assets(
    concept_name: str,
    raw_signal: str,
    archetype: str,
    niche: str,
    shopify_title: str,
    product_types: list[str],
) -> dict:
    """
    Generate complete Instagram marketing package for a design.
    Returns content dict stored in marketing_assets.content.
    """
    products_str = ", ".join(product_types)
    prompt = (
        f"Product: \"{shopify_title}\"\n"
        f"Concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche}\n"
        f"Design archetype: {archetype}\n"
        f"Available as: {products_str}\n\n"
        "Generate Instagram marketing content:\n"
        "- post_style: one of 'mockup', 'lifestyle', 'meme' — pick best for this niche/archetype\n"
        "- post_image_prompt: description of the post image to generate (if not using product mockup)\n"
        "- caption: 150-200 chars. Hook + body + CTA. Use niche voice. No hashtags here.\n"
        "- hashtags: array of 25-30 relevant hashtags (mix niche, product, trending)\n"
        "- story_variant: adapted short caption for vertical story format (max 80 chars)\n\n"
        "Reply with JSON: {"
        "\"post_style\": \"...\", \"post_image_prompt\": \"...\", "
        "\"caption\": \"...\", \"hashtags\": [...], \"story_variant\": \"...\""
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "instagram_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=1024,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        return {
            "post_style": data.get("post_style", "mockup"),
            "post_image_prompt": data.get("post_image_prompt", ""),
            "caption": str(data.get("caption", ""))[:200],
            "hashtags": data.get("hashtags", [])[:30],
            "story_variant": str(data.get("story_variant", ""))[:80],
        }
    except Exception as e:
        logger.error(f"Instagram generation failed for '{concept_name}': {e}")
        return {"caption": f"Check out our new {concept_name} design! Link in bio.", "hashtags": [niche]}
