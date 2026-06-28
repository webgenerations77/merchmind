"""Tests for DELETE /batches/{id}: removes terminal batches, refuses active ones."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

sys.modules.setdefault("redis", MagicMock())

from app.routers.batches import delete_batch


def _fake_db(batch):
    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value.first.return_value = batch
    q.filter.return_value.all.return_value = []      # no designs
    q.filter.return_value.delete.return_value = 0
    q.filter.return_value.update.return_value = 0
    return db


def test_delete_failed_batch_removes_row():
    batch = SimpleNamespace(id="b1", status="failed")
    db = _fake_db(batch)
    result = delete_batch(batch_id="b1", db=db, _="key")
    db.delete.assert_called_once_with(batch)
    db.commit.assert_called_once()
    assert result["data"]["deleted"] is True


def test_delete_running_batch_rejected():
    batch = SimpleNamespace(id="b1", status="running")
    db = _fake_db(batch)
    with pytest.raises(HTTPException) as exc:
        delete_batch(batch_id="b1", db=db, _="key")
    assert exc.value.status_code == 409
    db.delete.assert_not_called()


def test_delete_pending_approval_batch_rejected():
    batch = SimpleNamespace(id="b1", status="pending_approval")
    db = _fake_db(batch)
    with pytest.raises(HTTPException) as exc:
        delete_batch(batch_id="b1", db=db, _="key")
    assert exc.value.status_code == 409


def test_delete_missing_batch_404():
    db = _fake_db(None)
    with pytest.raises(HTTPException) as exc:
        delete_batch(batch_id="missing", db=db, _="key")
    assert exc.value.status_code == 404
