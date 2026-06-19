"""
Builds style-locked image generation prompts using Claude Sonnet.
All prompts enforce flat design, white background, no text, screen-print safe.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_STYLE_LOCK = (
    "flat design, bold outlines, limited color palette (max 4 colors), "
    "white background, centered composition, no gradients, "
    "suitable for screen printing, commercial merchandise style, "
    "NO TEXT in the image"
)

_ARCHETYPE_TEMPLATES = {
    "illustration": (
        "A detailed flat-design illustration of {subject}. "
        "Clean vector style, bold outlines, 3-4 solid colors, "
        "centered on white background. {style_lock}"
    ),
    "hybrid": (
        "A flat-design illustration of {subject} with space for text overlay below. "
        "Bold outlines, limited color palette, centered composition. {style_lock}"
    ),
    "text_icon": (
        "A simple bold icon or symbol representing {subject}. "
        "Single recognizable graphic, flat design, strong silhouette, "
        "centered on white background. {style_lock}"
    ),
    "typographic": (
        "A stylized typographic design based on the concept of {subject}. "
        "Letters as art, bold and geometric, flat design. {style_lock}"
    ),
    "text_only": None,  # No image generation for text_only
}

_SYSTEM = (
    "You are an expert print-on-demand merchandise designer. "
    "Write concise, vivid image generation prompts that produce clean, "
    "screen-printable artwork. Never include text or words in image prompts. "
    "Reply with only the prompt text, no extra commentary."
)


def build_image_prompt(
    raw_signal: str,
    archetype: str,
    niche: str = "",
    concept_name: str = "",
) -> str | None:
    """
    Build a style-locked image generation prompt for the given archetype.
    Returns None for text_only (no image generation needed).
    """
    if archetype == "text_only":
        return None

    template = _ARCHETYPE_TEMPLATES.get(archetype, _ARCHETYPE_TEMPLATES["illustration"])
    if template is None:
        return None

    context = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Concept name: \"{concept_name or raw_signal}\"\n"
        f"Niche category: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n\n"
        f"Write a concise image generation prompt for this design. "
        f"Must include these exact constraints: \"{_STYLE_LOCK}\"\n"
        f"Be specific about the subject, style, and composition. "
        f"Max 100 words."
    )
    try:
        text, _ = claude.sonnet(
            "image_prompt_generation",
            [{"role": "user", "content": context}],
            system=_SYSTEM,
            max_tokens=200,
        )
        prompt = text.strip()
        # Ensure style lock is always included
        if "flat design" not in prompt.lower():
            prompt += f". {_STYLE_LOCK}"
        return prompt
    except Exception as e:
        logger.error(f"Prompt builder failed for '{raw_signal}': {e}")
        # Fallback to template
        subject = concept_name or raw_signal
        return template.format(subject=subject, style_lock=_STYLE_LOCK)


def generate_text_content(raw_signal: str, archetype: str, niche: str = "") -> dict:
    """
    Generate text content (slogans, phrases) for archetypes that include text.
    Returns {primary_text, secondary_text, tagline}.
    """
    prompt = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n\n"
        "Generate compelling text for a print-on-demand design:\n"
        "- primary_text: Main slogan or phrase (1-5 words, punchy)\n"
        "- secondary_text: Supporting text or subheading (optional, can be null)\n"
        "- tagline: Short descriptor (optional, can be null)\n\n"
        "Make it emotionally resonant, community-specific, and merchandise-ready.\n"
        "Reply with JSON: {\"primary_text\": \"...\", \"secondary_text\": null, \"tagline\": null}"
    )
    try:
        text, _ = claude.sonnet(
            "text_content_generation",
            [{"role": "user", "content": prompt}],
            max_tokens=128,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group()) if match else {"primary_text": raw_signal, "secondary_text": None, "tagline": None}
    except Exception as e:
        logger.error(f"Text content generation failed for '{raw_signal}': {e}")
        return {"primary_text": raw_signal, "secondary_text": None, "tagline": None}
