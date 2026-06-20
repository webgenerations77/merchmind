"""
Drew's Mind — custom idea endpoints.
Submit your own ideas and MerchMind generates designs from them,
bypassing trend scraping and scoring.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.custom_idea import CustomIdea
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/ideas", tags=["ideas"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_ideas(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """List all custom ideas."""
    ideas = db.query(CustomIdea).order_by(CustomIdea.created_at.desc()).limit(50).all()
    return _envelope([{
        "id": str(i.id),
        "input_text": i.input_text,
        "status": i.status,
        "design_id": str(i.design_id) if i.design_id else None,
        "preferences": i.preferences,
        "created_at": i.created_at.isoformat(),
    } for i in ideas])


@router.post("")
def create_idea(body: dict, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """
    Submit a custom idea. Design generation runs async on the Celery worker.
    Body: {text: "your idea", preferences: {archetype: "illustration", ...}}
    """
    text = body.get("text", "").strip()
    if not text:
        return _envelope(error="Text is required")

    preferences = body.get("preferences", {})

    idea = CustomIdea(
        input_text=text,
        source="drews_mind",
        status="pending",
        preferences=preferences,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    from app.tasks.idea_generator import generate_idea_design
    generate_idea_design.delay(str(idea.id))

    return _envelope({
        "id": str(idea.id),
        "status": "pending",
        "message": "Design generation started — check back shortly",
    })
