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
    Body: {text: "your idea", preferences: {archetype: "illustration", ...}, save_only: true}
    """
    text = body.get("text", "").strip()
    if not text:
        return _envelope(error="Text is required")

    preferences = body.get("preferences", {})
    save_only = body.get("save_only", False)

    idea = CustomIdea(
        input_text=text,
        source="drews_mind",
        status="saved" if save_only else "pending",
        preferences=preferences,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    if not save_only:
        from app.tasks.idea_generator import generate_idea_design
        generate_idea_design.delay(str(idea.id))

    return _envelope({
        "id": str(idea.id),
        "status": idea.status,
        "message": "Thought saved for later" if save_only else "Design generation started — check back shortly",
    })


@router.post("/{idea_id}/generate")
def generate_saved_idea(idea_id: str, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Generate a design from a previously saved idea."""
    idea = db.query(CustomIdea).filter(CustomIdea.id == idea_id).first()
    if not idea:
        return _envelope(error="Idea not found")
    if idea.status not in ("saved", "failed"):
        return _envelope(error=f"Idea is already {idea.status}")

    idea.status = "pending"
    db.commit()

    from app.tasks.idea_generator import generate_idea_design
    generate_idea_design.delay(str(idea.id))

    return _envelope({
        "id": str(idea.id),
        "status": "pending",
        "message": "Design generation started",
    })


@router.delete("/{idea_id}")
def delete_idea(idea_id: str, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Delete a saved idea."""
    idea = db.query(CustomIdea).filter(CustomIdea.id == idea_id).first()
    if not idea:
        return _envelope(error="Idea not found")
    db.delete(idea)
    db.commit()
    return _envelope({"deleted": True})
