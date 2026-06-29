"""Redis-backed JSON cache for the Printify catalog. Stale-serving + backoff."""
import json
import logging
import time
from functools import lru_cache

import redis as redis_lib

from app.config import settings

logger = logging.getLogger(__name__)

_BACKOFF_SCHEDULE = [60, 300, 900, 3600]  # seconds: 1m, 5m, 15m, 1h
_BACKOFF_KEY = "catalog:backoff"


def is_stale(refreshed_at_epoch: float | None, ttl_hours: float, now_epoch: float) -> bool:
    if refreshed_at_epoch is None:
        return True
    return (now_epoch - refreshed_at_epoch) > (ttl_hours * 3600)


class CatalogCache:
    def __init__(self, client=None):
        self._client = client if client is not None else redis_lib.from_url(settings.REDIS_URL)

    def get_json(self, key: str) -> dict | None:
        raw = self._client.get(key)
        if raw is None:
            logger.debug("catalog.cache miss key=%s", key)
            return None
        logger.debug("catalog.cache hit key=%s", key)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def set_json(self, key: str, value: dict) -> None:
        value = dict(value)
        value["_refreshed_at"] = time.time()
        self._client.set(key, json.dumps(value))
        logger.info("catalog.cache set key=%s", key)

    def refreshed_at(self, key: str) -> float | None:
        data = self.get_json(key)
        return data.get("_refreshed_at") if data else None

    def in_backoff(self, now_epoch: float) -> bool:
        data = self.get_json(_BACKOFF_KEY)
        if not data:
            return False
        return now_epoch < data.get("until", 0)

    def record_failure(self, now_epoch: float) -> None:
        data = self.get_json(_BACKOFF_KEY) or {"count": 0}
        count = int(data.get("count", 0))
        wait = _BACKOFF_SCHEDULE[min(count, len(_BACKOFF_SCHEDULE) - 1)]
        self._client.set(_BACKOFF_KEY, json.dumps({"count": count + 1, "until": now_epoch + wait}))
        logger.warning("catalog.cache refresh failure #%d, backoff %ds", count + 1, wait)

    def clear_backoff(self) -> None:
        self._client.delete(_BACKOFF_KEY)


@lru_cache(maxsize=1)
def get_catalog_cache() -> CatalogCache:
    return CatalogCache()
