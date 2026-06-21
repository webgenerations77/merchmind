"""
Classifies design archetype from a trend signal using Claude Haiku.
Archetypes: text_only, illustration, hybrid, typographic, text_icon.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_ARCHETYPES = ("text_only", "illustration", "hybrid", "typographic", "text_icon")
_VISUAL_ARCHETYPES = {"illustration", "hybrid", "text_icon"}
_TEXT_ARCHETYPES = {"text_only", "typographic"}

_SYSTEM = (
    "You are a print-on-demand merchandise design strategist. "
    "Your goal is to classify what design format best suits a given trend topic. "
    "Visual designs (illustration, hybrid, text_icon) perform well for visual topics. "
    "Text-only designs work great for slogans, quotes, humor, and wordplay. "
    "Choose honestly based on the topic — a good mix of visual and text designs is ideal. "
    "Always reply with valid JSON only."
)


def classify_archetype(raw_signal: str, source: str, niche: str = "", bias: str | None = None) -> str:
    """
    Classify the best design archetype for a trend signal.

    - text_only: Pure typography, no illustration. Best for slogans/statements.
    - typographic: Stylized letter-based design, text IS the art.
    - text_icon: Simple icon + text combo. Bold and clean.
    - illustration: Detailed vector illustration, no text in design.
    - hybrid: Illustration + text overlay.
    """
    niche_ctx = f"\nNiche category: {niche}" if niche else ""
    bias_ctx = ""
    if bias == "image_only":
        bias_ctx = (
            "\nIMPORTANT: This design slot is reserved for a pure visual design. "
            "You MUST choose 'illustration'. The design will be image-only with no text overlay."
        )
    elif bias == "image_text":
        bias_ctx = (
            "\nIMPORTANT: This design slot is reserved for an image-with-text design. "
            "You MUST choose either 'hybrid' or 'text_icon'. "
            "These designs combine a visual element with a text slogan overlay."
        )
    elif bias == "text":
        bias_ctx = (
            "\nIMPORTANT: This design slot is reserved for a text-based design. "
            "You MUST choose either 'text_only' or 'typographic'. "
            "These designs use text/slogans as the primary visual element."
        )
    prompt = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Source: {source}{niche_ctx}{bias_ctx}\n\n"
        "Which design archetype best suits this topic for merch?\n"
        "- illustration: Detailed character, scene, or object — image-first (great for visual topics)\n"
        "- hybrid: Illustration with supporting text (topics with both visual and verbal appeal)\n"
        "- text_icon: Simple recognizable icon + short text (clean, bold)\n"
        "- typographic: Letters/words styled as art (monogram, acronym, stylized word)\n"
        "- text_only: Pure text — slogans, quotes, humor, statements (perfect for wordplay and catchy phrases)\n\n"
        "Choose the archetype that genuinely fits the topic best.\n\n"
        "Reply with JSON: {\"archetype\": \"<one of the five options>\", \"reason\": \"<10 words>\"}"
    )
    try:
        text, _ = claude.haiku(
            "archetype_classification",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=64,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        archetype = data.get("archetype", "text_icon").lower()
        if archetype not in _ARCHETYPES:
            archetype = "text_icon"
        return archetype
    except Exception as e:
        logger.error(f"Archetype classification failed for '{raw_signal}': {e}")
        return "text_icon"


def select_image_api(archetype: str) -> str | None:
    """
    Select which image generation API to use based on archetype.
    Returns 'flux_schnell', 'dalle3', or None (skip image gen).
    Flux Schnell is preferred (~$0.003/image vs ~$0.03 for DALL-E).
    """
    if archetype in ("text_only", "typographic"):
        return None
    return "flux_schnell"
