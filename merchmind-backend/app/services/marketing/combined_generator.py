"""
Combined marketing asset generator — generates all 5 channels in a single Claude call.
Replaces 5 sequential Sonnet calls with 1, cutting marketing generation time by ~80%.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an expert multi-channel marketing strategist for merchandise brands. "
    "Create engaging, niche-specific content across all platforms that drives purchases. "
    "Reply with valid JSON only."
)


def generate_all_marketing_assets(
    concept_name: str,
    raw_signal: str,
    archetype: str,
    niche: str,
    shopify_title: str,
    product_types: list[str],
) -> dict[str, dict]:
    """
    Generate marketing content for all 5 channels in one Claude call.
    Returns {instagram: {...}, tiktok: {...}, pinterest: {...}, email: {...}, blog: {...}}.
    """
    # TODO: use stored social links for publishing
    products_str = ", ".join(product_types)
    prompt = (
        f"Product: \"{shopify_title}\"\n"
        f"Concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n"
        f"Available as: {products_str}\n\n"
        "Generate marketing content for ALL 5 channels below in a single JSON response.\n\n"
        "Reply with JSON containing these 5 keys:\n"
        "{\n"
        '  "instagram": {\n'
        '    "post_style": "mockup"|"lifestyle"|"meme",\n'
        '    "caption": "150-200 char caption with hook + CTA",\n'
        '    "hashtags": ["25-30 relevant hashtags"],\n'
        '    "story_variant": "short story caption (max 80 chars)"\n'
        "  },\n"
        '  "tiktok": {\n'
        '    "hook": "attention-grabbing first line (max 50 chars)",\n'
        '    "script_outline": "3-5 bullet points for a 15-30s video",\n'
        '    "caption": "TikTok caption with CTAs (max 150 chars)",\n'
        '    "sounds_suggestion": "trending sound or music style"\n'
        "  },\n"
        '  "pinterest": {\n'
        '    "pin_title": "SEO-optimized title (max 100 chars)",\n'
        '    "pin_description": "keyword-rich description (max 500 chars)",\n'
        '    "board_suggestion": "suggested board name"\n'
        "  },\n"
        '  "email": {\n'
        '    "subject_line": "email subject (max 60 chars)",\n'
        '    "preview_text": "preview text (max 90 chars)",\n'
        '    "body_headline": "headline for email body",\n'
        '    "body_copy": "2-3 sentence body copy",\n'
        '    "cta_text": "CTA button text"\n'
        "  },\n"
        '  "blog": {\n'
        '    "title": "SEO blog post title",\n'
        '    "excerpt": "2-3 sentence excerpt",\n'
        '    "outline": ["3-5 section headings for the post"]\n'
        "  }\n"
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "combined_marketing_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=2048,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in response")
        data = json.loads(match.group())

        defaults = {
            "instagram": {"caption": f"Check out our new {concept_name} design! Link in bio.", "hashtags": [niche or "merch"]},
            "tiktok": {"hook": f"New {concept_name} drop!", "caption": f"Get yours now! #{niche or 'merch'}"},
            "pinterest": {"pin_title": shopify_title, "pin_description": f"Trending {concept_name} design"},
            "email": {"subject_line": f"New drop: {concept_name}", "body_copy": f"Check out our latest {concept_name} design."},
            "blog": {"title": f"Why {concept_name} is trending", "excerpt": f"The latest trend in {niche or 'merch'}."},
        }

        result = {}
        for channel in ["instagram", "tiktok", "pinterest", "email", "blog"]:
            result[channel] = data.get(channel, defaults[channel])

        logger.info("combined_marketing.generate ok channels=5 concept=%s", concept_name[:30])
        return result

    except Exception as e:
        logger.error(f"Combined marketing generation failed for '{concept_name}': {e}")
        return {
            "instagram": {"caption": f"Check out our new {concept_name} design!", "hashtags": [niche or "merch"]},
            "tiktok": {"hook": f"New {concept_name} drop!", "caption": f"Get yours now!"},
            "pinterest": {"pin_title": shopify_title, "pin_description": concept_name},
            "email": {"subject_line": f"New drop: {concept_name}", "body_copy": concept_name},
            "blog": {"title": f"Why {concept_name} is trending", "excerpt": concept_name},
        }
