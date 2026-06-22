"""
Image generation via Flux Schnell (Replicate) and GPT Image (OpenAI).
Uses sync clients for compatibility with Celery worker tasks.
Flux Schnell is primary (~$0.003/image), DALL-E is fallback (~$0.03/image).
"""
import base64
import logging
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx
import openai

from app.config import settings
from app.utils.exceptions import (
    ContentPolicyRejectionError,
    ImageGenerationError,
    ImageGenerationTimeoutError,
    ImageProviderUnavailableError,
)
from app.utils.rate_limiter import openai_limiter, replicate_limiter
from app.utils.storage import storage

logger = logging.getLogger(__name__)

_TIMEOUT = 60
_MAX_RETRIES = 3
_FLUX_SCHNELL = "black-forest-labs/flux-schnell"
_REPLICATE_POLL_INTERVAL = 2
_REPLICATE_MAX_WAIT = 120


@dataclass
class GeneratedImage:
    url: str
    provider: str
    prompt: str


class DALLe3Service:
    def generate(self, prompt: str) -> bytes:
        for attempt in range(_MAX_RETRIES):
            try:
                openai_limiter.consume()
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    size="1024x1024",
                    quality="low",
                    n=1,
                )
                image_data = response.data[0].b64_json
                logger.info("dalle3.generate ok prompt_len=%d attempt=%d", len(prompt), attempt + 1)
                _log_image_usage("openai", "image_generate", "gpt-image-1", 0.03)
                return base64.b64decode(image_data)
            except openai.BadRequestError as e:
                if "content_policy_violation" in str(e).lower() or "safety" in str(e).lower():
                    raise ContentPolicyRejectionError(f"DALL-E content policy: {e}") from e
                raise ImageGenerationError(f"DALL-E bad request: {e}") from e
            except (ContentPolicyRejectionError, ImageGenerationError):
                raise
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("dalle3.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"DALL-E failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("DALL-E: unreachable")

    def health_check(self) -> dict:
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            client.models.list()
            return {"service": "dalle3", "ok": True}
        except Exception as e:
            return {"service": "dalle3", "ok": False, "error": str(e)}


class FluxSchnellService:
    def generate(self, prompt: str, aspect_ratio: str = "1:1") -> bytes:
        for attempt in range(_MAX_RETRIES):
            try:
                replicate_limiter.consume()
                prediction = self._create_prediction(prompt, aspect_ratio)
                image_url = self._poll_prediction(prediction["id"])
                with httpx.Client(timeout=_TIMEOUT) as http:
                    r = http.get(image_url)
                    r.raise_for_status()
                logger.info("flux_schnell.generate ok prompt_len=%d aspect=%s attempt=%d", len(prompt), aspect_ratio, attempt + 1)
                _log_image_usage("replicate", "image_generate", "flux-schnell", 0.003)
                return r.content
            except (ImageGenerationError, ContentPolicyRejectionError, ImageGenerationTimeoutError):
                raise
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("flux_schnell.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"Flux Schnell failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("Flux Schnell: unreachable")

    def _create_prediction(self, prompt: str, aspect_ratio: str = "1:1") -> dict:
        enhanced_prompt = (
            f"{prompt} "
            "Professional vector art, flat design, clean crisp edges, "
            "pure white background, no text, no watermark, print-ready merchandise design"
        )
        with httpx.Client(timeout=30) as http:
            r = http.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"},
                json={
                    "input": {
                        "prompt": enhanced_prompt,
                        "go_fast": True,
                        "num_outputs": 1,
                        "aspect_ratio": aspect_ratio,
                        "output_format": "png",
                        "output_quality": 100,
                        "num_inference_steps": 4,
                    },
                },
            )
            r.raise_for_status()
            return r.json()

    def _poll_prediction(self, prediction_id: str) -> str:
        deadline = time.monotonic() + _REPLICATE_MAX_WAIT
        while time.monotonic() < deadline:
            time.sleep(_REPLICATE_POLL_INTERVAL)
            with httpx.Client(timeout=30) as http:
                r = http.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"},
                )
                r.raise_for_status()
                data = r.json()
            status = data.get("status")
            if status == "succeeded":
                output = data.get("output")
                url = output[0] if isinstance(output, list) else output
                return str(url)
            if status in ("failed", "canceled"):
                raise ImageGenerationError(f"Flux prediction {prediction_id} {status}: {data.get('error')}")
        raise ImageGenerationTimeoutError(f"Flux prediction {prediction_id} timed out after {_REPLICATE_MAX_WAIT}s")

    def health_check(self) -> dict:
        try:
            r = httpx.get(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell",
                headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"},
                timeout=10,
            )
            return {"service": "flux_schnell", "ok": r.status_code == 200}
        except Exception as e:
            return {"service": "flux_schnell", "ok": False, "error": str(e)}


class ImageGeneratorService:
    def __init__(self) -> None:
        self._dalle3 = DALLe3Service()
        self._flux = FluxSchnellService()

    def health_check(self) -> dict:
        dalle_hc = self._dalle3.health_check()
        flux_hc = self._flux.health_check()
        return {
            "service": "image_generator",
            "ok": dalle_hc["ok"] or flux_hc["ok"],
            "providers": {"dalle3": dalle_hc, "flux_schnell": flux_hc},
        }


@lru_cache(maxsize=1)
def get_image_generator_service() -> ImageGeneratorService:
    return ImageGeneratorService()


def generate_image(prompt: str, api: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
    """Generate image. Tries Flux Schnell first, falls back to DALL-E."""
    svc = get_image_generator_service()
    providers = [("flux_schnell", svc._flux), ("dalle3", svc._dalle3)]
    if api == "dalle3":
        providers = list(reversed(providers))

    last_error: Exception = RuntimeError("No providers")
    for name, provider in providers:
        try:
            if name == "flux_schnell":
                return provider.generate(prompt, aspect_ratio=aspect_ratio), name
            else:
                return provider.generate(prompt), name
        except ContentPolicyRejectionError:
            raise
        except Exception as e:
            last_error = e
            logger.warning("generate_image fallback from %s error=%s", name, e)

    raise ImageProviderUnavailableError(f"Both providers failed: {last_error}") from last_error


def _log_image_usage(service: str, operation: str, model: str, cost: float):
    try:
        from app.database import SessionLocal
        from app.models.api_usage_log import ApiUsageLog
        db = SessionLocal()
        db.add(ApiUsageLog(service=service, operation=operation, model=model, estimated_cost=cost))
        db.commit()
        db.close()
    except Exception:
        pass
