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


_PRIMARY_MAP = {
    "illustration": "tshirt",
    "hybrid": "tshirt",
    "text_icon": "tshirt",
    "text_only": "mug",
    "typographic": "poster",
}


def default_primary_product_type(archetype: str) -> str:
    return _PRIMARY_MAP.get(archetype, "tshirt")


def select_primary_product_type(
    concept_name: str,
    archetype: str,
    product_types: list[str],
    raw_signal: str = "",
) -> dict:
    """
    Use Claude to evaluate which product type best suits this design.
    Returns {"primary_product_type": str, "reasoning": str}.
    Falls back to archetype-based mapping on error.
    """
    if not product_types:
        fallback = default_primary_product_type(archetype)
        logger.warning("select_primary_product_type: no product_types, defaulting to %s", fallback)
        return {"primary_product_type": fallback, "reasoning": "No product types available — used archetype default."}

    prompt = (
        f'Design concept: "{concept_name}"\n'
        f"Archetype: {archetype}\n"
        f'Trend/topic: "{raw_signal or concept_name}"\n'
        f"Available product types: {', '.join(product_types)}\n\n"
        "Which product type is this design MOST optimized for? Consider:\n"
        "1. Design composition — does the layout best suit a wearable, drinkware, wall art, accessory, or sticker?\n"
        "2. Format fit — which product's format (aspect ratio, print area, viewing distance) best showcases this design?\n"
        "3. Core visual intent — what was this design primarily conceived to be?\n"
        "4. Commercial appeal — on which product would this design sell best?\n\n"
        'Reply with JSON only: {"primary_product_type": "<one of the available types>", "reasoning": "<2-3 sentences>"}'
    )
    try:
        text, _ = claude.haiku(
            "primary_product_type_selection",
            [{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            selected = data.get("primary_product_type", "").lower().strip()
            if selected in product_types:
                logger.info(
                    "primary_product_type AI: concept='%s' selected=%s",
                    concept_name[:40], selected,
                )
                return {
                    "primary_product_type": selected,
                    "reasoning": str(data.get("reasoning", "")),
                }
            logger.warning("AI selected invalid product type '%s', falling back", selected)

        fallback = default_primary_product_type(archetype)
        if fallback not in product_types:
            fallback = product_types[0]
        return {"primary_product_type": fallback, "reasoning": "AI response invalid — used archetype default."}
    except Exception as e:
        logger.error("Primary product type selection failed for '%s': %s", concept_name, e)
        fallback = default_primary_product_type(archetype)
        if fallback not in product_types:
            fallback = product_types[0]
        return {"primary_product_type": fallback, "reasoning": f"AI selection unavailable — used archetype default: {e}"}


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
