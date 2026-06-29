"""Cross-batch trend de-duplication helpers.

Kept free of celery / batch_pipeline imports so it is unit-testable without
the Celery stack (the dev venv has no celery, so the rest of the suite avoids
importing batch_pipeline). batch_pipeline uses these to drop scraped concepts
already turned into designs or proposed in a recent batch.
"""
import re
from datetime import datetime, timedelta, timezone

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalize_concept(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    "Coffee Lovers: But First Coffee!" -> "coffee lovers but first coffee"
    """
    if not text:
        return ""
    no_punct = _PUNCT_RE.sub(" ", text.lower())
    return _WS_RE.sub(" ", no_punct).strip()


def build_seen_set(db, weeks: int = 8) -> set:
    """Normalized concepts to exclude from a new batch: every existing
    (non-deleted) design concept plus every trend raw_signal from the last
    `weeks` weeks."""
    from app.models.design import Design
    from app.models.trend import Trend

    seen: set = set()

    for (concept,) in db.query(Design.concept_name).filter(Design.is_deleted == False).all():  # noqa: E712
        norm = normalize_concept(concept)
        if norm:
            seen.add(norm)

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    for (raw,) in db.query(Trend.raw_signal).filter(Trend.created_at >= cutoff).all():
        norm = normalize_concept(raw)
        if norm:
            seen.add(norm)

    return seen
