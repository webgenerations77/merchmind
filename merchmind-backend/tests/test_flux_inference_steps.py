"""Regression test: Flux Schnell num_inference_steps must be within the model's
1-4 step limit. Passing >4 makes Replicate reject the prediction POST, which
silently falls the pipeline back to the ~10x pricier DALL-E. See root cause:
commit 0babc6a raised this from 4 to 8."""
from unittest.mock import patch

from app.services.design.image_generator import FluxSchnellService


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"id": "pred_test"}


class _FakeClient:
    """Captures the JSON payload posted to Replicate instead of hitting the network."""

    captured: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers=None, json=None):
        _FakeClient.captured["payload"] = json
        return _FakeResp()


def test_flux_prediction_uses_valid_inference_steps():
    _FakeClient.captured = {}
    with patch("app.services.design.image_generator.httpx.Client", _FakeClient):
        FluxSchnellService()._create_prediction("a friendly cat", aspect_ratio="1:1")

    steps = _FakeClient.captured["payload"]["input"]["num_inference_steps"]
    assert 1 <= steps <= 4, (
        f"Flux Schnell supports only 1-4 inference steps; payload sent {steps}. "
        "Values >4 are rejected by Replicate and force a DALL-E fallback."
    )
