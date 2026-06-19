"""
Email marketing asset generator using Claude Sonnet.
Generates subject variants, preview text, HTML body, and send time recommendation.
"""
import json
import logging
import re
from datetime import datetime, timedelta
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are an email marketing expert for merchandise brands. "
    "Write high-converting, niche-specific emails with strong subject lines. "
    "Reply with valid JSON only."
)


def generate_email_assets(
    concept_name: str,
    raw_signal: str,
    niche: str,
    shopify_title: str,
    product_types: list[str],
    shopify_url: str = "",
) -> dict:
    """
    Generate email marketing package.
    Returns content dict stored in marketing_assets.content.
    """
    products_str = ", ".join(product_types)
    prompt = (
        f"Product: \"{shopify_title}\"\n"
        f"Concept: \"{concept_name}\"\n"
        f"Niche: {niche}\n"
        f"Available as: {products_str}\n"
        f"Store URL: {shopify_url or '[STORE_URL]'}\n\n"
        "Generate email marketing content:\n"
        "- subject_variants: Array of 3 subject line options:\n"
        "  1. Curiosity-driven (create intrigue)\n"
        "  2. Direct/benefit-focused\n"
        "  3. Humor or personality-driven\n"
        "- preview_text: 90 chars max. Complements subject line.\n"
        "- body: Structured HTML email body with:\n"
        "  * Engaging headline\n"
        "  * Product feature blocks (what makes it special)\n"
        "  * Social proof hook\n"
        "  * CTA button\n"
        "  Keep under 300 words, mobile-friendly.\n"
        "- send_time_recommendation: ISO 8601 timestamp for optimal send time\n\n"
        "Reply with JSON: {"
        "\"subject_variants\": [...], \"preview_text\": \"...\", "
        "\"body\": \"<html>...\", \"send_time_recommendation\": \"...\""
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "email_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=2048,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        # Default send time: next Wednesday 10am if not provided
        default_send = (datetime.utcnow() + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0
        ).isoformat() + "Z"
        return {
            "subject_variants": data.get("subject_variants", [f"New drop: {shopify_title}"]),
            "preview_text": str(data.get("preview_text", ""))[:90],
            "body": str(data.get("body", "")),
            "send_time_recommendation": data.get("send_time_recommendation", default_send),
        }
    except Exception as e:
        logger.error(f"Email generation failed for '{concept_name}': {e}")
        return {
            "subject_variants": [f"New {niche} merch just dropped 🎉"],
            "preview_text": f"Check out our new {concept_name} design.",
            "body": f"<p>We just launched <strong>{shopify_title}</strong>!</p>",
            "send_time_recommendation": "",
        }
