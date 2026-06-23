"""
Builds style-locked image generation prompts using Claude Sonnet.
All prompts enforce flat design, white background, no text, screen-print safe.
Product-type-specific format templates ensure compositional suitability per product.
"""
import json
import logging
import re
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_STYLE_LOCK = (
    "Professional merchandise artwork style. Isolated subject on a plain solid white background (#FFFFFF). "
    "Centered composition with clean edges and generous whitespace around the subject. "
    "High contrast, vibrant saturated colors. No text, no letters, no words, no watermarks, no signatures. "
    "The design element should be clearly separated from the background with crisp edges. "
    "Print-ready quality at 300 DPI, sharp details, professional commercial design. "
    "No gradients bleeding into background, no subtle textures on background, pure white background only."
)

_STYLE_LOCK_TEXT_OVERLAY = (
    "Professional merchandise artwork style. Isolated subject on a plain solid white background (#FFFFFF). "
    "Centered composition with clean edges. Leave space at the bottom third for text overlay. "
    "High contrast, vibrant saturated colors. No baked-in text, no letters, no words — text will be composited separately. "
    "No watermarks, no signatures. "
    "The design element should be clearly separated from the background with crisp edges. "
    "Print-ready quality at 300 DPI, sharp details, professional commercial design. "
    "No gradients bleeding into background, no subtle textures on background, pure white background only."
)

_PRODUCT_BACKGROUND_CONTEXT = {
    "tshirt": {"bg": "dark", "text_color": "white or light colors", "reason": "printed on dark fabric"},
    "hat": {"bg": "dark", "text_color": "white or light colors", "reason": "embroidered/printed on dark fabric"},
    "mug": {"bg": "light", "text_color": "dark (near-black or deep saturated color)", "reason": "printed on white ceramic"},
    "phone_case": {"bg": "light", "text_color": "dark (near-black or deep saturated color)", "reason": "printed on light case surface"},
    "sticker": {"bg": "transparent", "text_color": "dark with outline/shadow for contrast", "reason": "die-cut on various surfaces"},
}

_PRODUCT_FORMAT_TEMPLATES = {
    "tshirt": {
        "aspect_ratio": "1:1",
        "composition": (
            "Centered chest-print composition with generous whitespace on all sides. "
            "Design occupies roughly 60-70% of the canvas vertically. "
            "Strong focal point designed for screen printing on fabric. "
            "Bold, readable from arm's length."
        ),
        "prompt_keywords": "t-shirt print design, chest graphic, screen-print ready",
    },
    "mug": {
        "aspect_ratio": "1:1",
        "composition": (
            "Wraparound-friendly composition — design works when viewed on a curved surface. "
            "Horizontally balanced so it reads well from any angle. "
            "No critical elements at extreme left/right edges. "
            "Bold colors that pop against white ceramic."
        ),
        "prompt_keywords": "mug print design, wraparound graphic, ceramic-ready artwork",
    },
    "phone_case": {
        "aspect_ratio": "9:16",
        "composition": (
            "Vertical rectangular format designed for a phone case. "
            "Central focal point with breathing room at edges for case curvature. "
            "Bold and intentional at small scale — avoid intricate fine details. "
            "Design accounts for camera cutout area at top."
        ),
        "prompt_keywords": "phone case design, vertical format, bold centered graphic, mobile accessory art",
    },
    "hat": {
        "aspect_ratio": "1:1",
        "composition": (
            "Compact emblem or badge-style composition for embroidery/patch area. "
            "Simple, recognizable at small scale (roughly 3x2 inches). "
            "Minimal detail, strong silhouette, 2-4 colors maximum. "
            "Think cap patch or embroidered logo — clean and iconic."
        ),
        "prompt_keywords": "hat patch design, embroidered emblem, cap badge, small-scale graphic",
    },
    "sticker": {
        "aspect_ratio": "1:1",
        "composition": (
            "Die-cut sticker composition with a clear, clean outline. "
            "Self-contained shape that works as a standalone element. "
            "Vibrant colors, strong contrast, no background dependency. "
            "Designed to look great at 3-4 inch size on laptops, water bottles, etc."
        ),
        "prompt_keywords": "die-cut sticker design, vinyl sticker art, laptop sticker, self-contained graphic",
    },
}

_ARCHETYPE_TEMPLATES = {
    "illustration": (
        "A striking, highly detailed professional illustration of {subject}. "
        "Bold graphic style with clean vector-like lines, rich saturated colors, "
        "detailed but not cluttered. Flat design aesthetic with subtle depth through color layering. "
        "Modern commercial art quality suitable for screen printing. "
        "Strong focal point, balanced composition. {style_lock}"
    ),
    "hybrid": (
        "A bold, eye-catching graphic design of {subject}. "
        "Strong visual impact with a clear central motif, professional quality with space for text overlay. "
        "Clean layered composition, vibrant colors with limited palette (3-5 colors), modern design aesthetic. "
        "Strong graphic style with bold shapes and contrast. {style_lock}"
    ),
    "text_icon": (
        "A bold, iconic symbol representing {subject}. "
        "Strong recognizable silhouette, modern and minimal with geometric precision. "
        "Flat design with 2-3 accent colors, clean graphic design, professional quality. "
        "Think modern app icon or badge design — simple, memorable, striking. {style_lock}"
    ),
    "typographic": (
        "A creative typographic art piece inspired by the concept of {subject}. "
        "Decorative letterforms as art, modern graphic design style with artistic flourishes. "
        "Hand-lettering aesthetic with clean execution. {style_lock}"
    ),
    "text_only": None,
}

_SYSTEM = (
    "You are an expert merchandise graphic designer who creates bestselling "
    "print-on-demand designs. Write vivid, specific image generation prompts "
    "that produce professional, eye-catching artwork people want to wear or display. "
    "Focus on bold visual impact, emotional resonance, and commercial appeal. "
    "Never include text or words in image prompts — the design should be purely visual. "
    "Always specify: the exact subject, art style (flat design, vector, graphic art), "
    "color palette (name 3-5 specific colors), composition, "
    "and rendering quality (sharp, clean edges, print-ready). "
    "CRITICAL: The generated image MUST visually represent the exact concept name provided. "
    "Do not reinterpret, abstract, or deviate from the literal subject. "
    "If the concept is 'Mountain Sunrise', the image must depict a mountain with a sunrise — "
    "not ocean waves, not a forest, not an abstract pattern. Stay faithful to the concept. "
    "IMPORTANT: Tailor composition and format to the specific product type. "
    "A phone case needs vertical format with central focus; "
    "a hat needs a compact emblem; a sticker needs a die-cut shape with high contrast, "
    "clean edges, and a design that works at small scale on both transparent and white backgrounds. "
    "Avoid: photorealism, 3D renders, complex scenes, busy backgrounds, gradients. "
    "Reply with only the prompt text, no extra commentary."
)


def _extract_subject_keywords(concept_name: str) -> list[str]:
    """Extract key subject words from a concept name for alignment validation."""
    stop_words = {
        "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for",
        "is", "it", "be", "as", "by", "with", "from", "this", "that", "its",
        "are", "was", "were", "been", "has", "had", "do", "does", "did",
        "but", "not", "no", "so", "if", "up", "out", "about", "into",
        "day", "week", "month", "year", "new", "best", "top", "big",
    }
    words = re.findall(r"[a-zA-Z]{3,}", concept_name.lower())
    return [w for w in words if w not in stop_words]


def _validate_prompt_alignment(prompt: str, concept_name: str) -> bool:
    """Check that the generated prompt contains at least one key subject word from the concept."""
    keywords = _extract_subject_keywords(concept_name)
    if not keywords:
        return True
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in keywords)


def get_product_format(product_type: str) -> dict:
    """Return format template for a product type. Defaults to tshirt format."""
    return _PRODUCT_FORMAT_TEMPLATES.get(product_type, _PRODUCT_FORMAT_TEMPLATES["tshirt"])


def get_product_background(product_type: str) -> dict:
    """Return background context (bg type, text color guidance) for a product type."""
    return _PRODUCT_BACKGROUND_CONTEXT.get(product_type, _PRODUCT_BACKGROUND_CONTEXT["tshirt"])


def build_image_prompt(
    raw_signal: str,
    archetype: str,
    niche: str = "",
    concept_name: str = "",
    product_type: str = "tshirt",
) -> str | None:
    """
    Build a style-locked image generation prompt for the given archetype and product type.
    Returns None for text_only (no image generation needed).
    The product_type determines compositional guidance (format, aspect ratio, keywords).
    """
    if archetype == "text_only":
        return None

    template = _ARCHETYPE_TEMPLATES.get(archetype, _ARCHETYPE_TEMPLATES["illustration"])
    if template is None:
        return None

    fmt = get_product_format(product_type)
    bg_ctx = get_product_background(product_type)

    will_composite_text = archetype in ("hybrid", "text_icon")
    style_lock = _STYLE_LOCK_TEXT_OVERLAY if will_composite_text else _STYLE_LOCK

    text_color_instruction = ""
    if archetype in ("hybrid", "text_icon", "typographic"):
        text_color_instruction = (
            f"\nTEXT COLOR REQUIREMENT:\n"
            f"- This product has a {bg_ctx['bg']} background ({bg_ctx['reason']})\n"
            f"- Any text or lettering elements must use {bg_ctx['text_color']}\n"
            f"- Do NOT use white text on light backgrounds or dark text on dark backgrounds\n"
        )

    text_overlay_note = ""
    if will_composite_text:
        text_overlay_note = (
            "\nNOTE: Text will be composited onto this image separately via Pillow. "
            "Do NOT bake any text into the image. Instead, leave clear space in the "
            "lower third of the composition for a text overlay band.\n"
        )

    context = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Concept name: \"{concept_name or raw_signal}\"\n"
        f"Niche category: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n"
        f"Target product: {product_type}\n\n"
        f"PRODUCT FORMAT REQUIREMENTS:\n"
        f"- Composition: {fmt['composition']}\n"
        f"- Style keywords: {fmt['prompt_keywords']}\n"
        f"{text_color_instruction}"
        f"{text_overlay_note}\n"
        f"Write an image generation prompt for this specific product format.\n"
        f"The design must be PURPOSE-BUILT for {product_type} — not a generic graphic repurposed.\n"
        f"Be specific about the subject, visual style, color palette, and composition.\n"
        f"Must include these constraints: \"{style_lock}\"\n"
        f"Max 120 words."
    )
    subject = concept_name or raw_signal
    try:
        text, _ = claude.sonnet(
            "image_prompt_generation",
            [{"role": "user", "content": context}],
            system=_SYSTEM,
            max_tokens=200,
        )
        prompt = text.strip()
        if "white background" not in prompt.lower():
            prompt += f". {style_lock}"

        if not _validate_prompt_alignment(prompt, subject):
            logger.warning(
                "prompt_builder: concept drift detected — concept='%s' not reflected in prompt='%s'. Using template fallback.",
                subject[:60], prompt[:120],
            )
            prompt = template.format(subject=subject, style_lock=style_lock)

        logger.info(
            "prompt_builder: product_type=%s archetype=%s prompt_preview='%s'",
            product_type, archetype, prompt[:120],
        )
        return prompt
    except Exception as e:
        logger.error(f"Prompt builder failed for '{raw_signal}': {e}")
        return template.format(subject=subject, style_lock=style_lock)


def preview_all_product_prompts(
    raw_signal: str,
    archetype: str,
    niche: str = "",
    concept_name: str = "",
) -> dict:
    """
    Generate prompts for ALL product types for a given concept.
    Returns {product_type: {prompt, aspect_ratio, composition, keywords, background}}.
    Used for reviewing format-specific prompts before a batch run.
    """
    all_types = ["tshirt", "mug", "phone_case", "hat", "sticker"]
    results = {}
    for pt in all_types:
        fmt = get_product_format(pt)
        bg = get_product_background(pt)
        prompt = build_image_prompt(raw_signal, archetype, niche, concept_name, product_type=pt)
        results[pt] = {
            "prompt": prompt,
            "aspect_ratio": fmt["aspect_ratio"],
            "composition": fmt["composition"],
            "keywords": fmt["prompt_keywords"],
            "background": bg["bg"],
            "text_color": bg["text_color"],
        }
    return results


def generate_text_content(raw_signal: str, archetype: str, niche: str = "") -> dict:
    """
    Generate text content for archetypes that include text.
    Produces 3 candidates, scores each against merch-readiness criteria,
    and selects the highest-scoring one.
    Returns {primary_text, secondary_text, tagline, text_concept_scoring}.
    """
    prompt = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n\n"
        "Generate 3 text concept candidates for a print-on-demand design.\n\n"
        "TEXT CONCEPT GUIDELINES:\n"
        "- Single words or very short phrases (1-4 words MAXIMUM)\n"
        "- Conceptually open — the reader fills in the meaning\n"
        "- Emotionally resonant — something you'd want on your body\n"
        "- Cultural currency — feels like something you'd see in an indie coffee shop, "
        "a street art installation, or a design museum gift shop, NOT a motivational poster\n"
        "- RIGHT direction examples: \"Yet\", \"Almost\", \"Still Here\", \"Enough\", \"Not Yet\", \"Keep\", \"More\"\n"
        "- WRONG direction examples: \"Nature Heals Us\", \"Live Your Best Life\", \"Good Vibes Only\"\n\n"
        "For each candidate, score it 1-10 on these criteria:\n"
        "- brevity: Is it 1-4 words? Single words score highest.\n"
        "- openness: Is the meaning conceptually open, not literal or prescriptive?\n"
        "- resonance: Would someone want this on their body? Does it carry emotional weight?\n"
        "- cultural_currency: Does it feel current, indie, design-forward — not corporate or corny?\n\n"
        "Reply with JSON:\n"
        "{\n"
        "  \"candidates\": [\n"
        "    {\n"
        "      \"primary_text\": \"...\",\n"
        "      \"secondary_text\": null,\n"
        "      \"scores\": {\"brevity\": 9, \"openness\": 8, \"resonance\": 9, \"cultural_currency\": 8},\n"
        "      \"total\": 34,\n"
        "      \"rationale\": \"one sentence why this works or doesn't\"\n"
        "    }\n"
        "  ],\n"
        "  \"selected\": 0\n"
        "}"
    )
    try:
        text, _ = claude.sonnet(
            "text_content_generation",
            [{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"primary_text": raw_signal, "secondary_text": None, "tagline": None, "text_concept_scoring": None}

        data = json.loads(match.group())
        candidates = data.get("candidates", [])
        if not candidates:
            return {"primary_text": raw_signal, "secondary_text": None, "tagline": None, "text_concept_scoring": None}

        selected_idx = data.get("selected", 0)
        if selected_idx >= len(candidates):
            selected_idx = 0

        best = max(candidates, key=lambda c: c.get("total", 0))
        if best.get("total", 0) > candidates[selected_idx].get("total", 0):
            selected_idx = candidates.index(best)

        winner = candidates[selected_idx]
        scoring = {
            "candidates": [
                {
                    "text": c.get("primary_text", ""),
                    "scores": c.get("scores", {}),
                    "total": c.get("total", 0),
                    "rationale": c.get("rationale", ""),
                }
                for c in candidates
            ],
            "selected_index": selected_idx,
        }

        logger.info(
            "text_content: topic='%s' winner='%s' score=%d/%d candidates",
            raw_signal[:40], winner.get("primary_text", "")[:30],
            winner.get("total", 0), len(candidates),
        )

        return {
            "primary_text": winner.get("primary_text"),
            "secondary_text": winner.get("secondary_text"),
            "tagline": None,
            "text_concept_scoring": scoring,
        }
    except Exception as e:
        logger.error(f"Text content generation failed for '{raw_signal}': {e}")
        return {"primary_text": raw_signal, "secondary_text": None, "tagline": None, "text_concept_scoring": None}
