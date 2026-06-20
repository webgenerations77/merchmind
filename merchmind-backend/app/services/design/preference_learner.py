"""
Preference learner — analyzes approve/reject patterns from FeedbackLog
and generates style preferences to guide future design generation.
"""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.design import Design
from app.models.feedback_log import FeedbackLog

logger = logging.getLogger(__name__)


def get_preference_summary(db: Session, weeks: int = 8) -> dict:
    """Analyze recent approve/reject patterns and return preference signals."""
    cutoff = datetime.utcnow().date() - timedelta(weeks=weeks)
    logs = db.query(FeedbackLog).filter(FeedbackLog.week >= cutoff).all()

    if not logs:
        return {"has_data": False}

    design_ids = [log.design_id for log in logs]
    designs = db.query(Design).filter(Design.id.in_(design_ids)).all()
    design_map = {d.id: d for d in designs}

    approved_archetypes: Counter = Counter()
    rejected_archetypes: Counter = Counter()
    approved_styles: list[str] = []
    rejected_styles: list[str] = []

    for log in logs:
        design = design_map.get(log.design_id)
        if not design:
            continue

        if log.action == "approved":
            approved_archetypes[design.archetype] += 1
            if design.design_style:
                approved_styles.append(design.design_style)
        elif log.action == "rejected":
            rejected_archetypes[design.archetype] += 1
            if design.design_style:
                rejected_styles.append(design.design_style)

    total_approved = sum(approved_archetypes.values())
    total_rejected = sum(rejected_archetypes.values())
    total = total_approved + total_rejected

    archetype_rates = {}
    all_archetypes = set(list(approved_archetypes.keys()) + list(rejected_archetypes.keys()))
    for arch in all_archetypes:
        a = approved_archetypes.get(arch, 0)
        r = rejected_archetypes.get(arch, 0)
        t = a + r
        archetype_rates[arch] = {
            "approved": a,
            "rejected": r,
            "total": t,
            "approval_rate": round(a / t, 2) if t > 0 else 0,
        }

    preferred = [a for a, stats in archetype_rates.items() if stats["approval_rate"] >= 0.7 and stats["total"] >= 3]
    avoided = [a for a, stats in archetype_rates.items() if stats["approval_rate"] <= 0.3 and stats["total"] >= 3]

    return {
        "has_data": True,
        "total_reviews": total,
        "approval_rate": round(total_approved / total, 2) if total > 0 else 0,
        "archetype_rates": archetype_rates,
        "preferred_archetypes": preferred,
        "avoided_archetypes": avoided,
        "weeks_analyzed": weeks,
    }


def get_prompt_preferences(db: Session) -> str:
    """Generate a preference string to append to image prompts based on learned patterns."""
    summary = get_preference_summary(db)
    if not summary["has_data"] or summary["total_reviews"] < 5:
        return ""

    parts = []
    if summary["preferred_archetypes"]:
        parts.append(f"Preferred styles: {', '.join(summary['preferred_archetypes'])}.")
    if summary["avoided_archetypes"]:
        parts.append(f"Avoid these styles: {', '.join(summary['avoided_archetypes'])}.")

    return " ".join(parts)
