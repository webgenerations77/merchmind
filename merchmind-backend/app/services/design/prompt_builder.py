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
    "Professional merchandise artwork style. Isolated subject on a plain solid white background. "
    "Centered composition with clean edges and plenty of whitespace around the subject. "
    "High contrast, vibrant colors. No text, no letters, no words, no watermarks. "
    "The design element should be clearly separated from the background. "
    "Print-ready quality, sharp details, professional commercial design."
)

_ARCHETYPE_TEMPLATES = {
    "illustration": (
        "A striking, professional illustration of {subject}. "
        "Bold graphic style with clean lines, rich saturated colors, "
        "detailed but not cluttered. Modern commercial art quality. {style_lock}"
    ),
    "hybrid": (
        "A bold, eye-catching graphic design of {subject}. "
        "Strong visual impact, professional quality with space for text overlay. "
        "Clean composition, vibrant colors, modern design aesthetic. {style_lock}"
    ),
    "text_icon": (
        "A bold, iconic symbol representing {subject}. "
        "Strong recognizable silhouette, modern and minimal. "
        "Clean graphic design, professional quality. {style_lock}"
    ),
    "typographic": (
        "A creative typographic art piece inspired by the concept of {subject}. "
        "Letters and shapes as art, modern graphic design style. {style_lock}"
    ),
    "text_only": None,
}

_SYSTEM = (
    "You are an expert merchandise graphic designer who creates bestselling "
    "print-on-demand designs. Write vivid, specific image generation prompts "
    "that produce professional, eye-catching artwork people want to wear. "
    "Focus on bold visual impact, emotional resonance, and commercial appeal. "
    "Never include text or words in image prompts — the design should be purely visual. "
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
        f"Write an image generation prompt for a bestselling merchandise design.\n"
        f"Think about what would look amazing on a t-shirt or hoodie — bold, eye-catching, "
        f"something people would proudly wear.\n"
        f"Be specific about the subject, visual style, color palette, and composition.\n"
        f"Must include these constraints: \"{_STYLE_LOCK}\"\n"
        f"Max 120 words."
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
