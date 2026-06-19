"""
Image generation via DALL-E 3 (OpenAI) and Stable Diffusion XL (Replicate).
Uses sync clients for compatibility with Celery worker tasks.
Falls back to the alternate provider on failure.
"""
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
_REPLICATE_SDXL = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
_REPLICATE_POLL_INTERVAL = 3
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
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    n=1,
                )
                image_url = response.data[0].url
                with httpx.Client(timeout=_TIMEOUT) as http:
                    r = http.get(image_url)
                    r.raise_for_status()
                logger.info("dalle3.generate ok prompt_len=%d attempt=%d", len(prompt), attempt + 1)
                return r.content
            except openai.BadRequestError as e:
                if "content_policy_violation" in str(e).lower() or "safety" in str(e).lower():
                    raise ContentPolicyRejectionError(f"DALL-E 3 content policy: {e}") from e
                raise ImageGenerationError(f"DALL-E 3 bad request: {e}") from e
            except (ContentPolicyRejectionError, ImageGenerationError):
                raise
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("dalle3.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"DALL-E 3 failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("DALL-E 3: unreachable")

    def health_check(self) -> dict:
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            client.models.list()
            return {"service": "dalle3", "ok": True}
        except Exception as e:
            return {"service": "dalle3", "ok": False, "error": str(e)}


class StableDiffusionService:
    def generate(self, prompt: str) -> bytes:
        for attempt in range(_MAX_RETRIES):
            try:
                replicate_limiter.consume()
                prediction = self._create_prediction(prompt)
                image_url = self._poll_prediction(prediction["id"])
                with httpx.Client(timeout=_TIMEOUT) as http:
                    r = http.get(image_url)
                    r.raise_for_status()
                logger.info("stable_diffusion.generate ok prompt_len=%d attempt=%d", len(prompt), attempt + 1)
                return r.content
            except (ImageGenerationError, ContentPolicyRejectionError, ImageGenerationTimeoutError):
                raise
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("stable_diffusion.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"Stable Diffusion failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("Stable Diffusion: unreachable")

    def _create_prediction(self, prompt: str) -> dict:
        with httpx.Client(timeout=30) as http:
            r = http.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {settings.REPLICATE_API_KEY}"},
                json={
                    "version": _REPLICATE_SDXL.split(":")[1],
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": (
                            "text, words, letters, watermark, signature, low quality, "
                            "blurry, realistic photo, photography, 3D render"
                        ),
                        "width": 1024,
                        "height": 1024,
                        "num_inference_steps": 30,
                        "guidance_scale": 7.5,
                        "scheduler": "K_EULER",
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
                    headers={"Authorization": f"Token {settings.REPLICATE_API_KEY}"},
                )
                r.raise_for_status()
                data = r.json()
            status = data.get("status")
            if status == "succeeded":
                output = data.get("output")
                url = output[0] if isinstance(output, list) else output
                return str(url)
            if status in ("failed", "canceled"):
                raise ImageGenerationError(f"Replicate prediction {prediction_id} {status}: {data.get('error')}")
        raise ImageGenerationTimeoutError(f"Replicate prediction {prediction_id} timed out after {_REPLICATE_MAX_WAIT}s")

    def health_check(self) -> dict:
        try:
            r = httpx.get(
                "https://api.replicate.com/v1/models/stability-ai/sdxl",
                headers={"Authorization": f"Token {settings.REPLICATE_API_KEY}"},
                timeout=10,
            )
            return {"service": "stable_diffusion", "ok": r.status_code == 200}
        except Exception as e:
            return {"service": "stable_diffusion", "ok": False, "error": str(e)}


class ImageGeneratorService:
    def __init__(self) -> None:
        self._dalle3 = DALLe3Service()
        self._sd = StableDiffusionService()

    def health_check(self) -> dict:
        dalle_hc = self._dalle3.health_check()
        sd_hc = self._sd.health_check()
        return {
            "service": "image_generator",
            "ok": dalle_hc["ok"] or sd_hc["ok"],
            "providers": {"dalle3": dalle_hc, "stable_diffusion": sd_hc},
        }


@lru_cache(maxsize=1)
def get_image_generator_service() -> ImageGeneratorService:
    return ImageGeneratorService()


def generate_image(prompt: str, api: str) -> tuple[bytes, str]:
    svc = get_image_generator_service()
    providers = [("dalle3", svc._dalle3), ("stable_diffusion", svc._sd)]
    if api != "dalle3":
        providers = list(reversed(providers))

    last_error: Exception = RuntimeError("No providers")
    for name, provider in providers:
        try:
            return provider.generate(prompt), name
        except ContentPolicyRejectionError:
            raise
        except Exception as e:
            last_error = e
            logger.warning("generate_image fallback from %s error=%s", name, e)

    raise ImageProviderUnavailableError(f"Both providers failed: {last_error}") from last_error
