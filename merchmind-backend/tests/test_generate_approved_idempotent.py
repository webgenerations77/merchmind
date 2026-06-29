"""Regression: generate_approved_designs must be idempotent. Celery delivers
at-least-once, so a duplicate/retried run can land on a batch that already
finished. Before the fix, the status guard raised, the except handler flipped
the (successful) batch to 'failed' and retried — crashing in a loop while the
generated designs sat fine in the queue. A terminal-status batch must no-op."""
from unittest.mock import MagicMock, patch

import pytest

# batch_pipeline imports celery; the local dev venv may not have it installed
# (the rest of the suite avoids importing this module for the same reason).
# Skip cleanly there; run wherever celery is present (CI / the Docker image).
pytest.importorskip("celery")

from app.tasks.batch_pipeline import generate_approved_designs  # noqa: E402


@patch("app.tasks.batch_pipeline.SessionLocal")
def test_noops_on_already_complete_batch(mock_session_local):
    batch = MagicMock()
    batch.status = "complete"
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = batch
    mock_session_local.return_value = db

    # Must return cleanly — no raise, no retry, no status change.
    result = generate_approved_designs.run("11111111-1111-1111-1111-111111111111")

    assert result is None
    assert batch.status == "complete"  # NOT flipped to "failed"


@patch("app.tasks.batch_pipeline.SessionLocal")
def test_noops_on_cancelled_batch(mock_session_local):
    batch = MagicMock()
    batch.status = "cancelled"
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = batch
    mock_session_local.return_value = db

    result = generate_approved_designs.run("22222222-2222-2222-2222-222222222222")

    assert result is None
    assert batch.status == "cancelled"
