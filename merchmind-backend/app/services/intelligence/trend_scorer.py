"""
Two-stage trend scoring pipeline using Claude Haiku.
Stage 1: Trend signal score (velocity, cross-source, trajectory).
Stage 2: Merch viability score (emotional resonance, visual potential, niche depth, saturation).
"""
import json
import logging
import re
from typing import Optional
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)

_SYSTEM_SCORER = (
    "You are a merchandise trend analyst. Your job is to evaluate trending topics "
    "for print-on-demand merchandise potential. Be concise and analytical. "
    "Always respond with valid JSON only."
)


def score_trend_signal(raw_signal: str, source: str, source_metadata: dict) -> dict:
    """
    Stage 1: Score trend velocity/momentum using Claude Haiku.
    Returns {trend_score: int, reasoning: str}.
    """
    prompt = (
        f"Trend signal: \"{raw_signal}\"\n"
        f"Source: {source}\n"
        f"Metadata: {json.dumps(source_metadata)}\n\n"
        "Score this trend signal 0-100 based on:\n"
        "- Trend velocity: how fast is it rising? (0-40 pts)\n"
        "- Cross-source presence: is it appearing in multiple places? (0-20 pts)\n"
        "- Trajectory: rising vs peaked vs declining (0-40 pts)\n\n"
        "Reply with JSON: {\"trend_score\": <int>, \"reasoning\": \"<one sentence>\"}"
    )
    try:
        text, _ = claude.haiku(
            "trend_signal_score",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM_SCORER,
            max_tokens=128,
        )
        data = json.loads(_extract_json(text))
        return {
            "trend_score": max(0, min(100, int(data.get("trend_score", 0)))),
            "reasoning": str(data.get("reasoning", "")),
        }
    except Exception as e:
        logger.error(f"Stage 1 scoring failed for '{raw_signal}': {e}")
        return {"trend_score": 0, "reasoning": "Scoring failed"}


def score_merch_viability(
    raw_signal: str,
    trend_score: int,
    cluster_keywords: list[str] = None,
    cluster_boost: int = 0,
) -> dict:
    """
    Stage 2: Score merch viability using Claude Haiku.
    Returns {viability_score: int, final_score: int, claude_reasoning: str}.
    """
    kw_context = ""
    if cluster_keywords:
        kw_context = f"\nActive niche cluster keywords: {', '.join(cluster_keywords[:10])}"

    prompt = (
        f"Trend topic: \"{raw_signal}\"\n"
        f"Trend signal score: {trend_score}/100{kw_context}\n\n"
        "Score merch viability 0-100 across these 4 dimensions (25 pts each):\n"
        "1. Emotional resonance: pride, humor, passion, nostalgia\n"
        "2. Visual potential: can this become a compelling image or slogan?\n"
        "3. Niche depth: tight passionate community vs broad generic topic\n"
        "4. Saturation risk: fresh angle vs oversaturated market (25 = very fresh)\n\n"
        "Reply with JSON: {"
        "\"viability_score\": <int 0-100>, "
        "\"breakdown\": {\"emotional\": <int>, \"visual\": <int>, \"niche\": <int>, \"saturation\": <int>}, "
        "\"claude_reasoning\": \"<one sentence summary for mobile review>\""
        "}"
    )
    try:
        text, _ = claude.haiku(
            "merch_viability_score",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM_SCORER,
            max_tokens=200,
        )
        data = json.loads(_extract_json(text))
        viability_score = max(0, min(100, int(data.get("viability_score", 0))))
        final_score = int((trend_score * 0.4) + (viability_score * 0.6)) + cluster_boost
        final_score = min(100, final_score)
        return {
            "viability_score": viability_score,
            "final_score": final_score,
            "claude_reasoning": str(data.get("claude_reasoning", "")),
        }
    except Exception as e:
        logger.error(f"Stage 2 scoring failed for '{raw_signal}': {e}")
        return {"viability_score": 0, "final_score": 0, "claude_reasoning": "Scoring failed"}


def check_risk(raw_signal: str, score: int, threshold: int = 35) -> dict:
    """
    Risk filter for signals above threshold.
    Checks for real people, brands, trademarks, recent tragedies.
    Returns {risk_flag: 'none'|'soft'|'hard', risk_reason: str|None}.
    """
    if score < threshold:
        return {"risk_flag": "none", "risk_reason": None}

    prompt = (
        f"Trend topic: \"{raw_signal}\"\n\n"
        "Check if this topic could create legal or reputational risk for a merchandise seller:\n"
        "- hard: real person's name, registered brand, trademarked phrase, "
        "very recent tragedy (flag and auto-reject)\n"
        "- soft: potentially sensitive, borderline, worth human review\n"
        "- none: completely safe for merchandise\n\n"
        "Reply with JSON: {\"risk_flag\": \"none\"|\"soft\"|\"hard\", \"risk_reason\": null | \"<reason>\"}"
    )
    try:
        text, _ = claude.haiku(
            "risk_filter",
            [{"role": "user", "content": prompt}],
            system=_SYSTEM_SCORER,
            max_tokens=128,
        )
        data = json.loads(_extract_json(text))
        flag = data.get("risk_flag", "none")
        if flag not in ("none", "soft", "hard"):
            flag = "none"
        return {
            "risk_flag": flag,
            "risk_reason": data.get("risk_reason"),
        }
    except Exception as e:
        logger.error(f"Risk check failed for '{raw_signal}': {e}")
        return {"risk_flag": "soft", "risk_reason": f"Risk check error: {e}"}


def _extract_json(text: str) -> str:
    """Extract JSON object from Claude's response text."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    raise ValueError(f"No JSON found in response: {text[:200]}")
