"""
Builds style-locked image generation prompts using Claude Sonnet.
All prompts enforce white background, no text, screen-print safe.
Product-type-specific format templates ensure compositional suitability per product.

DESIGN TYPE AUDIT (Section 1):
  Archetypes handled: illustration, hybrid, text_icon, typographic (text_only returns None)
  build_image_prompt() sends concept+product context to Claude Sonnet, returns the prompt
  For illustration: compositional constraints (breathing room, fill ratio) are appended
  For hybrid/text_icon: text overlay note is included, no compositional fill constraints
  _PRODUCT_BACKGROUND_CONTEXT provides per-product text color guidance
  _PRODUCT_FORMAT_TEMPLATES provides per-product aspect ratio and composition guidance
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
    "hoodie": {"bg": "dark", "text_color": "white or light colors", "reason": "printed on dark fabric"},
    "long_sleeve": {"bg": "dark", "text_color": "white or light colors", "reason": "printed on dark fabric"},
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
    "hoodie": {
        "aspect_ratio": "1:1",
        "composition": (
            "Centered chest-print composition for a hoodie front. "
            "Design occupies roughly 50-60% of the canvas — slightly smaller than a tee "
            "to account for the hoodie's thicker fabric and kangaroo pocket below. "
            "Bold, high-contrast artwork that reads well on heavy fleece."
        ),
        "prompt_keywords": "hoodie print design, chest graphic, streetwear art, screen-print ready",
    },
    "long_sleeve": {
        "aspect_ratio": "1:1",
        "composition": (
            "Centered chest-print composition with generous whitespace on all sides. "
            "Design occupies roughly 60-70% of the canvas vertically. "
            "Strong focal point designed for screen printing on fabric. "
            "Bold, readable from arm's length."
        ),
        "prompt_keywords": "long sleeve shirt print design, chest graphic, screen-print ready",
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

_IMAGE_ONLY_COMPOSITION = (
    "Centered graphic design on a white background. "
    "The main subject occupies approximately 65-75% of the frame, "
    "surrounded by generous white space on all sides. Not full-bleed. "
    "Designed as a chest print graphic for merchandise. "
    "Clean edges, suitable for background removal."
)

_IMAGE_ONLY_PRODUCT_NOTES = {
    "tshirt": "Chest print format. Subject centered in upper 60% of frame.",
    "hoodie": "Chest print format. Subject centered in upper 60% of frame.",
    "long_sleeve": "Chest print format. Subject centered in upper 60% of frame.",
    "hat": "Chest print format. Subject centered in upper 60% of frame.",
    "mug": "Horizontal wrap format. Subject centered, wider than tall.",
    "sticker": "High contrast. Works at small scale. Bold, not intricate. Clean silhouette.",
    "phone_case": "Vertical format. Bold centered graphic with clear focal point. Breathing room at top and bottom edges.",
    "poster": "Full canvas composition. The design may use the full frame — this is the only product type where full-bleed is acceptable.",
}

_ARCHETYPE_TEMPLATES = {
    "illustration": (
        "A striking illustration of {subject} with real visual personality. "
        "Bold graphic style — think screen-print poster art, retro risograph, or tattoo flash sheet. "
        "Rich saturated colors with an unexpected palette, strong outlines, confident linework. "
        "Detailed but not cluttered — every element earns its place. "
        "The kind of design that makes someone stop scrolling. {style_lock}"
    ),
    "hybrid": (
        "A bold, eye-catching graphic design of {subject} with attitude. "
        "Strong central motif with visual weight, designed to look great with text overlaid. "
        "Limited palette (3-5 colors) with at least one unexpected color choice. "
        "Pop art energy, streetwear aesthetic, or indie poster style. "
        "Layered composition with clear visual hierarchy. {style_lock}"
    ),
    "text_icon": (
        "A bold, iconic symbol representing {subject}. "
        "Strong recognizable silhouette with graphic punch — think band logo, skate brand emblem, "
        "or indie coffee shop badge. Geometric precision with a hand-crafted feel. "
        "Flat design with 2-3 accent colors, memorable at any size. {style_lock}"
    ),
    "typographic": (
        "A creative typographic art piece inspired by the concept of {subject}. "
        "Decorative letterforms as art — hand-lettering with character, not corporate fonts. "
        "Think vintage sign painting, gig poster lettering, or graffiti-influenced type. "
        "Artistic flourishes that feel intentional, not decorative. {style_lock}"
    ),
    "text_only": None,
}

_SYSTEM = (
    "You are an expert merchandise graphic designer who creates bestselling "
    "print-on-demand designs for indie brands and streetwear labels. "
    "Write vivid, specific image generation prompts that produce artwork with personality — "
    "designs people want to wear because they're cool, witty, or visually striking. "
    "Think design museum gift shop, not corporate clip art. "
    "Push for unexpected angles on the concept: clever visual metaphors, bold stylistic choices, "
    "interesting color combos, and compositions with attitude. "
    "Never include text or words in image prompts — the design should be purely visual. "
    "Always specify: the exact subject, a distinctive art style (retro risograph, bold pop art, "
    "minimal line art, psychedelic, woodcut, tattoo flash, screen-print aesthetic, etc.), "
    "a specific color palette (name 3-5 colors by name, not generic), composition details, "
    "and rendering quality (sharp, clean edges, print-ready). "
    "CRITICAL: The generated image MUST visually represent the exact concept name provided. "
    "Do not reinterpret or deviate from the literal subject — but DO make it visually interesting. "
    "IMPORTANT: Tailor composition and format to the specific product type. "
    "A phone case needs vertical format with central focus; "
    "a hat needs a compact emblem; a sticker needs a die-cut shape with high contrast, "
    "clean edges, and a design that works at small scale. "
    "Avoid: photorealism, 3D renders, generic clip art, boring symmetrical layouts, "
    "busy backgrounds, gradients into background. "
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
    if archetype in ("text_only", "image_with_text"):
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

        if archetype == "illustration":
            product_note = _IMAGE_ONLY_PRODUCT_NOTES.get(product_type, _IMAGE_ONLY_PRODUCT_NOTES["tshirt"])
            prompt = f"{prompt} {_IMAGE_ONLY_COMPOSITION} {product_note}"

        logger.info(
            "prompt_builder: product_type=%s archetype=%s prompt_preview='%s'",
            product_type, archetype, prompt[:120],
        )
        return prompt
    except Exception as e:
        logger.error(f"Prompt builder failed for '{raw_signal}': {e}")
        fallback = template.format(subject=subject, style_lock=style_lock)
        if archetype == "illustration":
            product_note = _IMAGE_ONLY_PRODUCT_NOTES.get(product_type, _IMAGE_ONLY_PRODUCT_NOTES["tshirt"])
            fallback = f"{fallback} {_IMAGE_ONLY_COMPOSITION} {product_note}"
        return fallback


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
    all_types = ["tshirt", "hoodie", "long_sleeve"]
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
        f"Concept: \"{raw_signal}\"\n"
        f"Niche: {niche or 'general'}\n"
        f"Design archetype: {archetype}\n\n"
        "Generate 3 candidates for the text that will appear ON this print-on-demand design.\n\n"
        "FIDELITY IS THE #1 RULE:\n"
        "- The text MUST stay faithful to the concept above. A shopper reading the text "
        "should clearly recognize the concept. NEVER replace it with an unrelated abstract word.\n"
        "- If the concept is already a short, punchy phrase (1-6 words) — e.g. a slogan, "
        "joke, or saying — PREFER using it directly (lightly cleaned / title-cased). "
        "Do not 'improve' it into something different.\n"
        "- If the concept is longer or descriptive, distill it into a short on-concept phrase "
        "that preserves its core meaning, humor, or wordplay.\n\n"
        "STYLE GUIDELINES (secondary to fidelity):\n"
        "- Keep it short: 1-5 words. Tight and punchy beats wordy.\n"
        "- Design-forward voice — indie coffee shop / street art, not corporate or corny.\n"
        "- On-concept examples: concept \"Touch Grass\" -> \"Touch Grass\" or \"Go Outside\"; "
        "concept \"van life conversion guide\" -> \"Van Life\" or \"Home Is Where You Park\"; "
        "concept \"powered by snacks and spite\" -> \"Snacks & Spite\" or \"Powered By Spite\".\n"
        "- OFF-concept (forbidden): turning \"Touch Grass\" into \"Dirt\", or "
        "\"powered by snacks and spite\" into \"Fueled\" — these lose the concept.\n\n"
        "For each candidate, score it 1-10 on these criteria:\n"
        "- fidelity: Does the text clearly connect to the concept above? (most important)\n"
        "- brevity: Is it 1-5 words? Tighter scores higher.\n"
        "- resonance: Would someone want this on their body? Does it carry weight or humor?\n"
        "- cultural_currency: Does it feel current, indie, design-forward — not corporate or corny?\n\n"
        "Reply with JSON:\n"
        "{\n"
        "  \"candidates\": [\n"
        "    {\n"
        "      \"primary_text\": \"...\",\n"
        "      \"secondary_text\": null,\n"
        "      \"scores\": {\"fidelity\": 9, \"brevity\": 9, \"resonance\": 9, \"cultural_currency\": 8},\n"
        "      \"total\": 35,\n"
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
