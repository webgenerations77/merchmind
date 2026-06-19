"""
Image generation via DALL-E 3 (OpenAI) and Stable Diffusion XL (Replicate).
Async-first; falls back to the alternate provider on failure.
Uploads raw output to Supabase Storage and returns the public URL.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx
from openai import AsyncOpenAI, BadRequestError as OpenAIBadRequestError

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

_TIMEOUT = 30
_MAX_RETRIES = 3
_REPLICATE_SDXL = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
_REPLICATE_POLL_INTERVAL = 2
_REPLICATE_MAX_WAIT = 120


@dataclass
class GeneratedImage:
    url: str
    provider: str
    prompt: str


class DALLe3Service:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(self, prompt: str) -> bytes:
        for attempt in range(_MAX_RETRIES):
            try:
                openai_limiter.consume()
                response = await self._client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    style="natural",
                    n=1,
                    response_format="url",
                )
                image_url = response.data[0].url
                async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
                    r = await http.get(image_url)
                    r.raise_for_status()
                logger.info("dalle3.generate ok prompt_len=%d attempt=%d", len(prompt), attempt + 1)
                return r.content
            except OpenAIBadRequestError as e:
                if "content_policy_violation" in str(e).lower() or "safety" in str(e).lower():
                    raise ContentPolicyRejectionError(f"DALL-E 3 content policy: {e}") from e
                raise ImageGenerationError(f"DALL-E 3 bad request: {e}") from e
            except asyncio.TimeoutError as e:
                raise ImageGenerationTimeoutError("DALL-E 3 timed out") from e
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("dalle3.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"DALL-E 3 failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("DALL-E 3: unreachable")

    def health_check(self) -> dict:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            client.models.list()
            return {"service": "dalle3", "ok": True}
        except Exception as e:
            return {"service": "dalle3", "ok": False, "error": str(e)}


class StableDiffusionService:
    async def generate(self, prompt: str) -> bytes:
        for attempt in range(_MAX_RETRIES):
            try:
                replicate_limiter.consume()
                prediction = await self._create_prediction(prompt)
                image_url = await self._poll_prediction(prediction["id"])
                async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
                    r = await http.get(image_url)
                    r.raise_for_status()
                logger.info("stable_diffusion.generate ok prompt_len=%d attempt=%d", len(prompt), attempt + 1)
                return r.content
            except (ImageGenerationError, ContentPolicyRejectionError, ImageGenerationTimeoutError):
                raise
            except Exception as e:
                wait = 2 ** attempt * 3
                logger.warning("stable_diffusion.generate attempt=%d/%d failed error=%s wait=%ds", attempt + 1, _MAX_RETRIES, e, wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                else:
                    raise ImageProviderUnavailableError(f"Stable Diffusion failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ImageGenerationError("Stable Diffusion: unreachable")

    async def _create_prediction(self, prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.post(
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

    async def _poll_prediction(self, prediction_id: str) -> str:
        deadline = time.monotonic() + _REPLICATE_MAX_WAIT
        while time.monotonic() < deadline:
            await asyncio.sleep(_REPLICATE_POLL_INTERVAL)
            async with httpx.AsyncClient(timeout=30) as http:
                r = await http.get(
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
            import httpx as _httpx
            r = _httpx.get(
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

    async def generate_and_upload(self, prompt: str, design_id: str, api: str = "dalle3") -> GeneratedImage:
        """
        Generate image with the specified provider, fall back to the other on failure.
        Uploads raw bytes to Supabase and returns the public URL.
        """
        providers = [("dalle3", self._dalle3), ("stable_diffusion", self._sd)]
        if api != "dalle3":
            providers = list(reversed(providers))

        last_error: Exception | None = None
        for name, provider in providers:
            try:
                image_bytes = await provider.generate(prompt)
                path = storage.design_raw_path(design_id)
                url = storage.upload(path, image_bytes, "image/png")
                logger.info("image_generator.generate_and_upload design_id=%s provider=%s url=%s", design_id, name, url)
                return GeneratedImage(url=url, provider=name, prompt=prompt)
            except ContentPolicyRejectionError:
                raise
            except Exception as e:
                logger.warning("image_generator.generate_and_upload provider=%s failed error=%s, trying fallback", name, e)
                last_error = e

        raise ImageProviderUnavailableError(f"Both image providers failed. Last error: {last_error}") from last_error

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


# ─── Sync backwards-compat wrappers (used by existing pipeline tasks) ─────────

def generate_dalle3(prompt: str) -> bytes:
    return asyncio.run(DALLe3Service().generate(prompt))


def generate_stable_diffusion(prompt: str) -> bytes:
    return asyncio.run(StableDiffusionService().generate(prompt))


def generate_image(prompt: str, api: str) -> tuple[bytes, str]:
    svc = get_image_generator_service()
    # For sync callers that don't have a design_id, upload is skipped; they get bytes directly
    providers = [("dalle3", svc._dalle3), ("stable_diffusion", svc._sd)]
    if api != "dalle3":
        providers = list(reversed(providers))

    last_error: Exception = RuntimeError("No providers")
    for name, provider in providers:
        try:
            return asyncio.run(provider.generate(prompt)), name
        except ContentPolicyRejectionError:
            raise
        except Exception as e:
            last_error = e
            logger.warning("generate_image fallback from %s error=%s", name, e)

    raise ImageProviderUnavailableError(f"Both providers failed: {last_error}") from last_error
