"""
Regression tests for the Claude client request timeout.

Background: on 2026-06-29 a batch wedged at status="running" for 24+ min because
a scoring Claude call hung with no timeout (SDK default 600s/attempt). The client
now sets a bounded timeout so hangs raise APITimeoutError and surface as
ClaudeTimeoutError for callers to fall back on, instead of hanging forever.
"""
from unittest.mock import patch

import anthropic
import httpx
import pytest

from app.utils.claude_client import ClaudeClient, ClaudeTimeoutError


def test_client_constructed_with_bounded_timeout():
    client = ClaudeClient()
    # SDK default is 600s — anything that large would re-introduce the wedge.
    assert client._client.timeout is not None
    assert float(client._client.timeout) <= 120.0


def test_timeout_surfaces_as_claude_timeout_error():
    client = ClaudeClient()
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    with patch.object(client._client.messages, "create",
                      side_effect=anthropic.APITimeoutError(request=req)), \
         patch("app.utils.claude_client.time.sleep"):  # don't actually back off
        with pytest.raises(ClaudeTimeoutError):
            client.haiku("test_task", [{"role": "user", "content": "hi"}])
