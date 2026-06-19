"""
Font pair selection using Claude Haiku from a curated font library.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_FONT_LIBRARY = [
    "Bebas Neue",
    "Oswald",
    "Nunito",
    "Playfair Display",
    "Anton",
    "Montserrat",
    "Pacifico",
    "Roboto Condensed",
    "Impact",
    "Raleway",
    "Permanent Marker",
    "Abril Fatface",
]

_SYSTEM = (
    "You are a print-on-demand merchandise typography specialist. "
    "Select font pairs that are bold, readable at small sizes, "
    "and appropriate for the niche and mood. Reply with valid JSON only."
)


def select_font_pair(
    raw_signal: str,
    archetype: str,
    niche: str = "",
    primary_text: str = "",
) -> dict:
    """
    Select primary and secondary font for a design using Claude Haiku.
    Returns {primary_font, secondary_font, reasoning}.
    """
    font_list = "\n".join(f"- {f}" for f in _FONT_LIBRARY)
    prompt = (
        f"Design topic: \"{raw_signal}\"\n"
        f"Primary text: \"{primary_text or raw_signal}\"\n"
        f"Archetype: {archetype}\n"
        f"Niche: {niche or 'general'}\n\n"
        f"Available fonts:\n{font_list}\n\n"
        "Select the best font pair for this merchandise design. "
        "Primary font for the main text, secondary font for supporting text.\n"
        "Consider: mood, readability at shirt-size, niche fit.\n\n"
        "Reply with JSON: {"
        "\"primary_font\": \"<font name>\", "
        "\"secondary_font\": \"<font name or null>\", "
        "\"reasoning\": \"<one sentence>\""
        "}"
    )
    try:
        text, _ = claude.haiku(
            "font_selection",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=128,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        primary = data.get("primary_font", "Bebas Neue")
        secondary = data.get("secondary_font")
        if primary not in _FONT_LIBRARY:
            primary = "Bebas Neue"
        if secondary and secondary not in _FONT_LIBRARY:
            secondary = "Montserrat"
        return {
            "primary_font": primary,
            "secondary_font": secondary,
            "font_pair": f"{primary} / {secondary}" if secondary else primary,
            "reasoning": data.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Font selection failed for '{raw_signal}': {e}")
        return {
            "primary_font": "Bebas Neue",
            "secondary_font": "Montserrat",
            "font_pair": "Bebas Neue / Montserrat",
            "reasoning": "Default fallback",
        }
