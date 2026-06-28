"""
Regression test for the generate-approved endpoint: it must flip the batch
status to "running" synchronously before dispatching the Celery task, so the
dashboard's status poll doesn't revert the UI to the approval gate during
worker-pickup latency.
"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# The batches router instantiates a redis client at import time; the test
# environment has no redis package, so stub it before importing the router.
sys.modules.setdefault("redis", MagicMock())

from app.routers.batches import generate_approved


def _fake_db(batch):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = batch
    return db


def test_generate_approved_sets_running_before_dispatch():
    batch = SimpleNamespace(id="b1", status="pending_approval")
    db = _fake_db(batch)

    # The endpoint does `from app.tasks.batch_pipeline import generate_approved_designs`
    # inside the handler; that module pulls heavy deps, so stub it in sys.modules.
    fake_bp = MagicMock()
    fake_bp.generate_approved_designs.delay.return_value = SimpleNamespace(id="task-123")
    with patch.dict(sys.modules, {"app.tasks.batch_pipeline": fake_bp}):
        result = generate_approved(batch_id="b1", body=None, db=db, _="key")

    # Status flipped synchronously and committed before the task was dispatched.
    assert batch.status == "running"
    db.commit.assert_called_once()
    fake_bp.generate_approved_designs.delay.assert_called_once()
    assert result["data"]["task_id"] == "task-123"


def test_generate_approved_rejects_terminal_batch():
    batch = SimpleNamespace(id="b1", status="complete")
    db = _fake_db(batch)

    with pytest.raises(HTTPException) as exc:
        generate_approved(batch_id="b1", body=None, db=db, _="key")
    assert exc.value.status_code == 409


def test_generate_approved_missing_batch_404():
    db = _fake_db(None)
    with pytest.raises(HTTPException) as exc:
        generate_approved(batch_id="missing", body=None, db=db, _="key")
    assert exc.value.status_code == 404
