"""
Batch management endpoints including SSE progress streaming.
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis as redis_lib

from app.database import get_db
from app.models.batch import Batch
from app.schemas.batch import BatchOut
from app.routers.auth import verify_api_key
from app.config import settings

router = APIRouter(prefix="/batches", tags=["batches"])
logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_batches(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batches = db.query(Batch).order_by(Batch.created_at.desc()).limit(50).all()
    return _envelope([BatchOut.model_validate(b).model_dump() for b in batches])


@router.get("/current")
def get_current_batch(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batch = db.query(Batch).order_by(Batch.created_at.desc()).first()
    if not batch:
        return _envelope(None)
    return _envelope(BatchOut.model_validate(batch).model_dump())


@router.get("/{batch_id}")
def get_batch(batch_id: UUID, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    return _envelope(BatchOut.model_validate(batch).model_dump())


@router.post("/trigger")
def trigger_batch(_: str = Depends(verify_api_key)):
    """Manually trigger the weekly batch pipeline now."""
    from app.tasks.batch_pipeline import run_weekly_batch
    task = run_weekly_batch.delay()
    return _envelope({"task_id": task.id, "message": "Batch pipeline triggered"})


@router.get("/{batch_id}/progress")
async def stream_batch_progress(batch_id: UUID, _: str = Depends(verify_api_key)):
    """
    SSE endpoint: streams batch progress events in real-time.
    Clients receive JSON events as the pipeline advances through steps.
    """
    channel = f"batch_progress:{batch_id}"

    async def event_generator():
        pubsub = _redis.pubsub()
        pubsub.subscribe(channel)
        try:
            # First send current batch state
            yield f"data: {json.dumps({'type': 'connected', 'batch_id': str(batch_id)})}\n\n"
            # Stream events for up to 2 hours
            timeout = 7200
            elapsed = 0
            while elapsed < timeout:
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                await asyncio.sleep(0.1)
                elapsed += 1
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
