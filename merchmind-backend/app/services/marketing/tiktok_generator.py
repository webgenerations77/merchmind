"""
TikTok marketing asset generator using Claude Sonnet.
Generates hook text, overlay script, audio suggestion, and concept format.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a viral TikTok content strategist for merchandise brands. "
    "Create scroll-stopping, pattern-interrupt content that gets views and drives sales. "
    "Reply with valid JSON only."
)

_CONCEPT_FORMATS = ("POV", "starter_pack", "relatable", "trend_hijack")


def generate_tiktok_assets(
    concept_name: str,
    raw_signal: str,
    niche: str,
    shopify_title: str,
) -> dict:
    """
    Generate TikTok content package.
    Returns content dict stored in marketing_assets.content.
    """
    prompt = (
        f"Product: \"{shopify_title}\"\n"
        f"Concept: \"{concept_name}\"\n"
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche}\n\n"
        "Generate TikTok video content plan:\n"
        "- hook: First 3 seconds on-screen text. Max 10 words. Must pattern-interrupt.\n"
        "- overlay_script: Array of {{\"timestamp\": \"0:00\", \"text\": \"...\"}} objects "
        "for text overlays throughout a 15-30 second video\n"
        "- audio_suggestion: {{\"category\": \"...\", \"mood\": \"...\"}} "
        "(e.g. trending audio, upbeat pop, comedy sound)\n"
        "- concept_format: one of 'POV', 'starter_pack', 'relatable', 'trend_hijack'\n\n"
        "Reply with JSON: {"
        "\"hook\": \"...\", \"overlay_script\": [...], "
        "\"audio_suggestion\": {...}, \"concept_format\": \"...\""
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "tiktok_generation",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=768,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        fmt = data.get("concept_format", "relatable")
        if fmt not in _CONCEPT_FORMATS:
            fmt = "relatable"
        return {
            "hook": str(data.get("hook", ""))[:60],
            "overlay_script": data.get("overlay_script", []),
            "audio_suggestion": data.get("audio_suggestion", {"category": "trending", "mood": "upbeat"}),
            "concept_format": fmt,
        }
    except Exception as e:
        logger.error(f"TikTok generation failed for '{concept_name}': {e}")
        return {"hook": f"POV: You found the perfect {niche} gift 👀", "concept_format": "POV"}
