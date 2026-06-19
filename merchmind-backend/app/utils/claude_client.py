"""
Anthropic API wrapper with model routing, rate limit handling, and usage logging.
"""
import time
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
import anthropic
from app.config import settings

logger = logging.getLogger(__name__)


class ClaudeRateLimitError(Exception):
    pass


class ClaudeAPIError(Exception):
    pass


class ClaudeTimeoutError(Exception):
    pass


@dataclass
class ClaudeUsageLog:
    model: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost_estimate_usd: float
    duration_ms: int


# Cost per million tokens (input / output)
_MODEL_COSTS = {
    settings.HAIKU_MODEL: (0.80, 4.00),
    settings.SONNET_MODEL: (3.00, 15.00),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = _MODEL_COSTS.get(model, (3.00, 15.00))
    return (input_tokens / 1_000_000 * costs[0]) + (output_tokens / 1_000_000 * costs[1])


class ClaudeClient:
    """Routes to Haiku for fast/cheap tasks, Sonnet for creative/vision tasks."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._haiku = settings.HAIKU_MODEL
        self._sonnet = settings.SONNET_MODEL

    def _call(
        self,
        model: str,
        task_type: str,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 1024,
        max_retries: int = 3,
    ) -> tuple[str, ClaudeUsageLog]:
        """Execute API call with exponential backoff retry."""
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            t0 = time.monotonic()
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                }
                if system:
                    kwargs["system"] = system

                response = self._client.messages.create(**kwargs)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                usage = response.usage
                log = ClaudeUsageLog(
                    model=model,
                    task_type=task_type,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_estimate_usd=_estimate_cost(model, usage.input_tokens, usage.output_tokens),
                    duration_ms=elapsed_ms,
                )
                logger.info(
                    "claude_call",
                    extra={
                        "model": model,
                        "task_type": task_type,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cost_usd": log.cost_estimate_usd,
                        "duration_ms": elapsed_ms,
                    },
                )
                return response.content[0].text, log

            except anthropic.RateLimitError as e:
                wait = min(2 ** attempt * 10, 120)
                logger.warning(
                    f"Claude rate limit on attempt {attempt + 1}/{max_retries}; "
                    f"retrying in {wait}s"
                )
                time.sleep(wait)
                last_error = ClaudeRateLimitError(
                    f"Claude rate limit exceeded after {max_retries} attempts: {e}"
                )

            except anthropic.APITimeoutError as e:
                last_error = ClaudeTimeoutError(f"Claude API timed out on task '{task_type}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt * 2)
                else:
                    raise last_error

            except anthropic.APIError as e:
                raise ClaudeAPIError(
                    f"Claude API error on task '{task_type}' (model={model}): {e}"
                ) from e

        raise last_error  # type: ignore[misc]

    # ── Haiku shortcuts (scoring, classification, cheap tasks) ──────────────

    def haiku(
        self,
        task_type: str,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 512,
    ) -> tuple[str, ClaudeUsageLog]:
        """Call claude-haiku — for scoring, classification, font selection."""
        return self._call(self._haiku, task_type, messages, system, max_tokens)

    # ── Sonnet shortcuts (creative copy, vision, image prompts) ─────────────

    def sonnet(
        self,
        task_type: str,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> tuple[str, ClaudeUsageLog]:
        """Call claude-sonnet — for creative copy, vision scoring, marketing."""
        return self._call(self._sonnet, task_type, messages, system, max_tokens)

    def sonnet_vision(
        self,
        task_type: str,
        image_url: str,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> tuple[str, ClaudeUsageLog]:
        """Call claude-sonnet with an image for vision quality scoring."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "url", "url": image_url},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return self._call(self._sonnet, task_type, messages, system, max_tokens)


claude = ClaudeClient()
