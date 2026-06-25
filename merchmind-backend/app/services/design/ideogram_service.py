"""
Ideogram image generation for the image_with_text archetype.
Generates a single image with integrated illustration + styled typography.
Uses Ideogram V_2 with DESIGN style for merch-appropriate output.
"""
import logging
import time

import httpx

from app.config import settings
from app.utils.exceptions import ImageGenerationError, ImageProviderUnavailableError
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.ideogram.ai"
_TIMEOUT = 90
_MAX_RETRIES = 2

_ASPECT_RATIO_MAP = {
    "phone_case": "ASPECT_9_16",
}
_DEFAULT_ASPECT = "ASPECT_1_1"

_MERCH_SUFFIX = (
    "White background. Centered composition. Clean edges suitable "
    "for print-on-demand merchandise. Not full-bleed."
)


def _build_prompt(image_description: str, text_content: str) -> str:
    """Build an Ideogram prompt with text-in-image syntax."""
    return (
        f"{image_description}, with bold stylized text reading '{text_content}'. "
        f"{_MERCH_SUFFIX}"
    )


def _get_aspect_ratio(product_type: str) -> str:
    return _ASPECT_RATIO_MAP.get(product_type, _DEFAULT_ASPECT)


def generate_ideogram_image(
    image_description: str,
    text_content: str,
    product_type: str = "tshirt",
    layout_suggestion: str = "integrated",
) -> tuple[bytes, str]:
    """
    Generate an image via Ideogram with integrated text.
    Returns (image_bytes, full_prompt).
    Raises ImageGenerationError on failure.
    """
    if not settings.IDEOGRAM_API_KEY:
        raise ImageGenerationError(
            "IDEOGRAM_API_KEY is not set. Add it to .env before using image_with_text designs."
        )

    prompt = _build_prompt(image_description, text_content)
    aspect_ratio = _get_aspect_ratio(product_type)

    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(timeout=_TIMEOUT) as http:
                response = http.post(
                    f"{_BASE_URL}/generate",
                    headers={
                        "Api-Key": settings.IDEOGRAM_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "image_request": {
                            "prompt": prompt,
                            "aspect_ratio": aspect_ratio,
                            "model": "V_2",
                            "style_type": "DESIGN",
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            images = data.get("data", [])
            if not images:
                raise ImageGenerationError(
                    f"Ideogram returned no images. Response: {data}"
                )

            image_url = images[0].get("url")
            if not image_url:
                raise ImageGenerationError(
                    f"Ideogram response missing image URL. Response: {data}"
                )

            with httpx.Client(timeout=60) as http:
                img_resp = http.get(image_url)
                img_resp.raise_for_status()

            _log_image_usage()
            logger.info(
                "ideogram.generate ok prompt_len=%d aspect=%s attempt=%d",
                len(prompt), aspect_ratio, attempt + 1,
            )
            return img_resp.content, prompt

        except (ImageGenerationError, ImageProviderUnavailableError):
            raise
        except httpx.HTTPStatusError as e:
            error_body = e.response.text[:500] if e.response else ""
            if attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt * 3
                logger.warning(
                    "ideogram.generate attempt=%d/%d failed status=%s body=%s wait=%ds",
                    attempt + 1, _MAX_RETRIES, e.response.status_code, error_body, wait,
                )
                time.sleep(wait)
            else:
                raise ImageGenerationError(
                    f"Ideogram API error after {_MAX_RETRIES} attempts: "
                    f"status={e.response.status_code} body={error_body} prompt={prompt}"
                ) from e
        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt * 3
                logger.warning(
                    "ideogram.generate attempt=%d/%d failed error=%s wait=%ds",
                    attempt + 1, _MAX_RETRIES, e, wait,
                )
                time.sleep(wait)
            else:
                raise ImageProviderUnavailableError(
                    f"Ideogram failed after {_MAX_RETRIES} attempts: {e} prompt={prompt}"
                ) from e

    raise ImageGenerationError("Ideogram: unreachable")


def generate_and_store(
    design_id: str,
    image_description: str,
    text_content: str,
    product_type: str = "tshirt",
) -> tuple[str, str, str]:
    """
    Generate via Ideogram, run bg removal, upload to Supabase.
    Returns (raw_url, processed_url, prompt).
    """
    image_bytes, prompt = generate_ideogram_image(
        image_description, text_content, product_type,
    )

    raw_path = storage.design_raw_path(design_id)
    raw_url = storage.upload(raw_path, image_bytes)

    from app.services.design.bg_remover import remove_white_background
    clean_bytes = remove_white_background(image_bytes)

    proc_path = storage.design_processed_path(design_id)
    processed_url = storage.upload(proc_path, clean_bytes)

    logger.info(
        "ideogram.store design=%s raw=%d processed=%d",
        design_id[:8], len(image_bytes), len(clean_bytes),
    )
    return raw_url, processed_url, prompt


def _log_image_usage():
    try:
        from app.database import SessionLocal
        from app.models.api_usage_log import ApiUsageLog
        db = SessionLocal()
        db.add(ApiUsageLog(
            service="ideogram",
            operation="image_generate",
            model="ideogram-v2",
            estimated_cost=0.08,
        ))
        db.commit()
        db.close()
    except Exception:
        pass
