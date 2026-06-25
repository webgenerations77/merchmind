"""
Classifies design archetype from a trend signal using Claude Haiku.
Archetypes: text_only, illustration, hybrid, typographic, text_icon.

DESIGN TYPE AUDIT (Section 1):
  _ARCHETYPES = (text_only, illustration, hybrid, typographic, text_icon)
  _VISUAL_ARCHETYPES = {illustration, hybrid, text_icon} → get image generation
  _TEXT_ARCHETYPES = {text_only, typographic} → skip image gen, use text_preview
  select_image_api: text_only/typographic → None, all others → flux_schnell
  classify_archetype accepts bias param: image_only, text, image_text
  Fallback on error: text_icon
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_ARCHETYPES = ("text_only", "illustration", "hybrid", "typographic", "text_icon", "image_with_text")
_VISUAL_ARCHETYPES = {"illustration", "hybrid", "text_icon", "image_with_text"}
_TEXT_ARCHETYPES = {"text_only", "typographic"}

_SYSTEM = (
    "You are a print-on-demand merchandise design strategist. "
    "Your goal is to classify what design format best suits a given trend topic. "
    "Visual designs (illustration, hybrid, text_icon) perform well for visual topics. "
    "image_with_text designs are best when a concept shines as an illustration paired with a short evocative word or phrase — Ideogram renders the text directly into the image. "
    "Text-only designs work great for slogans, quotes, humor, and wordplay. "
    "Choose honestly based on the topic — a good mix of visual and text designs is ideal. "
    "Always reply with valid JSON only."
)


def classify_archetype(raw_signal: str, source: str, niche: str = "", bias: str | None = None) -> str | dict:
    """
    Classify the best design archetype for a trend signal.

    Returns a string for most archetypes, or a dict for image_with_text
    containing {archetype, image_description, text_content, layout_suggestion}.

    - text_only: Pure typography, no illustration. Best for slogans/statements.
    - typographic: Stylized letter-based design, text IS the art.
    - text_icon: Simple icon + text combo. Bold and clean.
    - illustration: Detailed vector illustration, no text in design.
    - hybrid: Illustration + text overlay.
    - image_with_text: Integrated image + styled text via Ideogram.
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
    elif bias == "image_with_text":
        bias_ctx = (
            "\nIMPORTANT: This design slot is reserved for an integrated image-with-text design via Ideogram. "
            "You MUST choose 'image_with_text'. "
            "Choose a concept where a bold illustrated element paired with 1-4 evocative words makes the strongest design."
        )
    prompt = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Source: {source}{niche_ctx}{bias_ctx}\n\n"
        "Which design archetype best suits this topic for merch?\n"
        "- illustration: Detailed character, scene, or object — image-first (great for visual topics)\n"
        "- hybrid: Illustration with supporting text (topics with both visual and verbal appeal)\n"
        "- text_icon: Simple recognizable icon + short text (clean, bold)\n"
        "- image_with_text: Integrated image + styled typography in one design — best when a visual element paired with an evocative word or short phrase makes the concept strongest (e.g. illustrated icon with the word 'YET' in bold stylized type). Uses Ideogram for built-in text rendering.\n"
        "- typographic: Letters/words styled as art (monogram, acronym, stylized word)\n"
        "- text_only: Pure text — slogans, quotes, humor, statements (perfect for wordplay and catchy phrases)\n\n"
        "Choose the archetype that genuinely fits the topic best.\n\n"
        "If you choose image_with_text, also provide:\n"
        "- image_description: describe the visual/illustration component only (no text in image_description)\n"
        "- text_content: the text to appear in the design (1-4 words)\n"
        "- layout_suggestion: always \"integrated\"\n\n"
        "Reply with JSON: {\"archetype\": \"<one of the six options>\", \"reason\": \"<10 words>\", ...optional image_with_text fields}"
    )
    try:
        text, _ = claude.haiku(
            "archetype_classification",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=200,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        archetype = data.get("archetype", "text_icon").lower()
        if archetype not in _ARCHETYPES:
            archetype = "text_icon"
        if archetype == "image_with_text":
            return {
                "archetype": archetype,
                "image_description": data.get("image_description", ""),
                "text_content": data.get("text_content", ""),
                "layout_suggestion": "integrated",
            }
        return archetype
    except Exception as e:
        logger.error(f"Archetype classification failed for '{raw_signal}': {e}")
        return "text_icon"


def select_image_api(archetype: str) -> str | None:
    """
    Select which image generation API to use based on archetype.
    Returns 'flux_schnell', 'dalle3', 'ideogram', or None (skip image gen).
    Flux Schnell is preferred (~$0.003/image vs ~$0.03 for DALL-E).
    image_with_text uses Ideogram for integrated text-in-image generation.
    """
    if archetype in ("text_only", "typographic"):
        return None
    if archetype == "image_with_text":
        return "ideogram"
    return "flux_schnell"
