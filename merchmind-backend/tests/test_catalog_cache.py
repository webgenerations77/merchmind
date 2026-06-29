import json
from app.services.catalog.cache import is_stale, CatalogCache


class FakeRedis:
    """Minimal in-memory stand-in for the redis client methods we use."""
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def set(self, k, v):
        self.store[k] = v

    def delete(self, *ks):
        for k in ks:
            self.store.pop(k, None)


HOUR = 3600.0


def test_is_stale_none_is_always_stale():
    assert is_stale(None, 24, now_epoch=1000.0) is True


def test_is_stale_within_ttl_is_fresh():
    assert is_stale(1000.0, 24, now_epoch=1000.0 + 23 * HOUR) is False


def test_is_stale_past_ttl_is_stale():
    assert is_stale(1000.0, 24, now_epoch=1000.0 + 25 * HOUR) is True


def test_set_then_get_roundtrips_and_stamps():
    cache = CatalogCache(client=FakeRedis())
    cache.set_json("catalog:blueprints", {"items": [1, 2, 3]})
    got = cache.get_json("catalog:blueprints")
    assert got["items"] == [1, 2, 3]
    assert isinstance(got["_refreshed_at"], (int, float))
    assert cache.refreshed_at("catalog:blueprints") == got["_refreshed_at"]


def test_get_missing_returns_none():
    cache = CatalogCache(client=FakeRedis())
    assert cache.get_json("nope") is None
    assert cache.refreshed_at("nope") is None


def test_backoff_grows_with_failures():
    cache = CatalogCache(client=FakeRedis())
    assert cache.in_backoff(now_epoch=1000.0) is False
    cache.record_failure(now_epoch=1000.0)          # 60s window
    assert cache.in_backoff(now_epoch=1030.0) is True
    assert cache.in_backoff(now_epoch=1070.0) is False
    cache.clear_backoff()
    assert cache.in_backoff(now_epoch=1071.0) is False
