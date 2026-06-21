"""
Quality scoring for generated designs using Claude Sonnet with vision.
Scores 4 dimensions (0-10 each): clarity, appeal, suitability, originality.
Threshold: 28/40. Below threshold: regenerate once → force text_only.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_THRESHOLD = 28
_SYSTEM = (
    "You are an expert merchandise quality evaluator. "
    "Assess designs for commercial print-on-demand viability. "
    "Be objective and consistent. Reply with valid JSON only."
)


def score_design_quality(
    image_url: str,
    concept_name: str,
    archetype: str,
    niche: str = "",
    threshold: int = _THRESHOLD,
) -> dict:
    """
    Score design quality using Claude Sonnet vision.
    Returns {total: int, breakdown: dict, passes_threshold: bool, reasoning: str}.
    """
    prompt = (
        f"Design concept: \"{concept_name}\"\n"
        f"Archetype: {archetype}\n"
        f"Niche: {niche or 'general'}\n\n"
        "Score this merchandise design on 4 dimensions (0-10 each):\n"
        "1. concept_clarity: Is the message instantly clear? (0=confusing, 10=crystal clear)\n"
        "2. visual_appeal: Is it eye-catching and polished? (0=ugly, 10=professional)\n"
        "3. merch_suitability: Will it look good on a shirt/mug/etc.? (0=not suitable, 10=perfect)\n"
        "4. originality: Is it fresh and distinctive? (0=generic/copied, 10=highly original)\n\n"
        "Reply with JSON: {"
        "\"concept_clarity\": <0-10>, "
        "\"visual_appeal\": <0-10>, "
        "\"merch_suitability\": <0-10>, "
        "\"originality\": <0-10>, "
        "\"reasoning\": \"<one sentence summary>\""
        "}"
    )
    try:
        text, _ = claude.sonnet_vision(
            "design_quality_score",
            image_url=image_url,
            prompt=prompt,
            system=_SYSTEM,
            max_tokens=256,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}

        breakdown = {
            "concept_clarity": max(0, min(10, int(data.get("concept_clarity", 0)))),
            "visual_appeal": max(0, min(10, int(data.get("visual_appeal", 0)))),
            "merch_suitability": max(0, min(10, int(data.get("merch_suitability", 0)))),
            "originality": max(0, min(10, int(data.get("originality", 0)))),
        }
        total = sum(breakdown.values())
        return {
            "total": total,
            "breakdown": breakdown,
            "passes_threshold": total >= threshold,
            "reasoning": str(data.get("reasoning", "")),
        }
    except Exception as e:
        logger.error(f"Quality scoring failed for '{concept_name}': {e}")
        return {
            "total": 28,
            "breakdown": {"concept_clarity": 7, "visual_appeal": 7, "merch_suitability": 7, "originality": 7},
            "passes_threshold": True,
            "reasoning": f"Quality scoring unavailable — auto-passed: {e}",
        }


def select_primary_product_type(archetype: str) -> str:
    _PRIMARY_MAP = {
        "illustration": "tshirt",
        "hybrid": "tshirt",
        "text_icon": "tshirt",
        "text_only": "mug",
        "typographic": "poster",
    }
    return _PRIMARY_MAP.get(archetype, "tshirt")


def assign_product_bundle(archetype: str, quality_breakdown: dict, max_products: int = 6) -> list[str]:
    """
    Assign product types based on archetype and quality.
    Always includes at least 5 types. Returns list of product type strings.
    """
    all_types = ["tshirt", "mug", "hat", "phone_case", "sticker", "poster"]

    if archetype == "illustration":
        types = ["tshirt", "mug", "poster", "phone_case", "sticker"]
    elif archetype in ("text_only", "typographic"):
        types = ["tshirt", "mug", "hat", "phone_case", "sticker", "poster"]
    elif archetype == "text_icon":
        types = ["tshirt", "mug", "hat", "phone_case", "sticker"]
    else:
        types = ["tshirt", "mug", "hat", "phone_case", "sticker", "poster"]

    for t in all_types:
        if t not in types:
            types.append(t)

    return types[:max_products]
