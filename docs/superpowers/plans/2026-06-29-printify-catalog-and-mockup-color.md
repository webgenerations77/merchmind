# Printify Catalog Service + Mockup Color Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Redis-cached Printify catalog service with zero hardcoded IDs, and use it to fix always-black t-shirt mockups by harvesting per-color mockups from created products and adding a per-product-type color picker to the review queue.

**Architecture:** A new `app/services/catalog/` namespace fetches blueprint/provider/variant/color-name data from the Printify Catalog API and caches it in Redis (24h TTL, background refresh, stale-serving, exponential backoff). Hex codes, per-variant cost, and per-color mockup URLs are *not* in the catalog API — they are harvested from created Printify products via `ingest_product()` (bootstrapped from existing shop products, kept fresh by the batch pipeline). The dashboard reads colors from new `/catalog` endpoints and swaps mockups using per-product `color_mockups` data.

**Tech Stack:** Python 3.11, FastAPI, Celery, Redis (`redis` lib, already used), SQLAlchemy + Alembic + Postgres JSONB, `httpx`, `pytest` + `unittest.mock`. Dashboard: React + TypeScript + Vite + Tailwind, axios.

## Global Constraints

- **Zero hardcoded Printify IDs / color names / variant IDs / blueprint IDs in new code.** Existing maps in `printify_publisher.py` (`_BLUEPRINT_MAP`, `_PROVIDER_MAP`) remain only as a fallback safety net.
- **`is_light` computed from hex brightness, never a hardcoded list:** `is_light = (R*299 + G*587 + B*114) / 1000 > 128`.
- **Cache reads must never block** a request or app startup; reads serve from Redis, refresh runs in background.
- **Color name normalization:** lowercase + collapse internal whitespace for keys; preserve a `display_name`.
- **Approval → Printify publish → Shopify draft flow is unchanged.** Two-store `target_store` logic, the Dynamic-Mockups→Pillow fallback chain, and `PrintifyService`'s public interface stay as-is.
- **Color is per product type** (stored on `Product`, not `Design`).
- **Run all backend commands from `merchmind-backend/`.** Venv Python: `.venv/Scripts/python.exe` on Windows. Tests: `pytest`. Migrations auto-run on app startup and are mirrored into `_apply_critical_schema_fallback()` in `main.py`.
- **New env tunables:** `PRINTIFY_CATALOG_TTL_HOURS=24`, `PRINTIFY_MAX_COLORS_PER_PRODUCT=25`.

---

# Phase 1 — Catalog foundation

## Task 1: Config tunables + `.env.example`

**Files:**
- Modify: `merchmind-backend/app/config.py:73-91` (add two settings near Batch settings)
- Modify: `merchmind-backend/.env.example`
- Test: `merchmind-backend/tests/test_catalog_config.py`

**Interfaces:**
- Produces: `settings.PRINTIFY_CATALOG_TTL_HOURS: int` (default 24), `settings.PRINTIFY_MAX_COLORS_PER_PRODUCT: int` (default 25).

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_config.py
from app.config import settings


def test_catalog_tunables_have_defaults():
    assert settings.PRINTIFY_CATALOG_TTL_HOURS == 24
    assert settings.PRINTIFY_MAX_COLORS_PER_PRODUCT == 25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_config.py -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'PRINTIFY_CATALOG_TTL_HOURS'`

- [ ] **Step 3: Add the settings**

In `app/config.py`, after the `REQUIRE_TREND_APPROVAL` block (around line 83), add:

```python
    # Printify catalog cache
    PRINTIFY_CATALOG_TTL_HOURS: int = 24
    PRINTIFY_MAX_COLORS_PER_PRODUCT: int = 25
```

- [ ] **Step 4: Document in `.env.example`**

Append to `merchmind-backend/.env.example` (near the Printify vars):

```
# Printify catalog cache tuning
PRINTIFY_CATALOG_TTL_HOURS=24
PRINTIFY_MAX_COLORS_PER_PRODUCT=25
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_catalog_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/config.py .env.example tests/test_catalog_config.py
git commit -m "feat(catalog): add catalog cache tunables to config and .env.example"
```

---

## Task 2: Color math helpers (`colors.py`)

Pure functions, no external deps — the foundation everything else uses.

**Files:**
- Create: `merchmind-backend/app/services/catalog/__init__.py` (empty)
- Create: `merchmind-backend/app/services/catalog/colors.py`
- Test: `merchmind-backend/tests/test_catalog_colors.py`

**Interfaces:**
- Produces:
  - `normalize_color_name(name: str) -> str`
  - `hex_to_rgb(hex_str: str) -> tuple[int, int, int]`
  - `brightness(rgb: tuple[int, int, int]) -> float`
  - `is_light_hex(hex_str: str) -> bool`
  - `nearest_color(target_hex: str, candidates: dict[str, str]) -> str | None` — `candidates` is `{normalized_name: hex}`; returns the normalized name of the closest hex by Euclidean RGB distance, or `None` if empty.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_colors.py
from app.services.catalog.colors import (
    normalize_color_name, hex_to_rgb, brightness, is_light_hex, nearest_color,
)


def test_normalize_collapses_case_and_whitespace():
    assert normalize_color_name("Navy  Blue") == "navy blue"
    assert normalize_color_name(" Heather Grey ") == "heather grey"


def test_hex_to_rgb_handles_hash_and_no_hash():
    assert hex_to_rgb("#ffffff") == (255, 255, 255)
    assert hex_to_rgb("000000") == (0, 0, 0)


def test_brightness_formula():
    # (255*299 + 255*587 + 255*114)/1000 = 255
    assert brightness((255, 255, 255)) == 255.0
    assert brightness((0, 0, 0)) == 0.0


def test_is_light_threshold():
    assert is_light_hex("#ffffff") is True
    assert is_light_hex("#000000") is False
    # mid grey 0x80 = 128 → not > 128 → dark
    assert is_light_hex("#808080") is False


def test_nearest_color_picks_closest_hex():
    candidates = {"black": "#000000", "white": "#ffffff", "navy": "#001f3f"}
    assert nearest_color("#101010", candidates) == "black"
    assert nearest_color("#f0f0f0", candidates) == "white"


def test_nearest_color_empty_returns_none():
    assert nearest_color("#123456", {}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_colors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.catalog'`

- [ ] **Step 3: Create the package and implementation**

Create empty `merchmind-backend/app/services/catalog/__init__.py`.

Create `merchmind-backend/app/services/catalog/colors.py`:

```python
"""Pure color math helpers for the Printify catalog service. No external deps."""
import re


def normalize_color_name(name: str) -> str:
    """Lowercase and collapse internal whitespace for use as a stable key."""
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = (hex_str or "").lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_str!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def brightness(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (r * 299 + g * 587 + b * 114) / 1000


def is_light_hex(hex_str: str) -> bool:
    return brightness(hex_to_rgb(hex_str)) > 128


def nearest_color(target_hex: str, candidates: dict[str, str]) -> str | None:
    """Return the normalized name of the candidate whose hex is closest to target."""
    if not candidates:
        return None
    tr, tg, tb = hex_to_rgb(target_hex)
    best_name, best_dist = None, None
    for name, hex_str in candidates.items():
        try:
            r, g, b = hex_to_rgb(hex_str)
        except ValueError:
            continue
        dist = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
        if best_dist is None or dist < best_dist:
            best_name, best_dist = name, dist
    return best_name
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_catalog_colors.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/catalog/__init__.py app/services/catalog/colors.py tests/test_catalog_colors.py
git commit -m "feat(catalog): add pure color math helpers"
```

---

## Task 3: Redis cache layer (`cache.py`)

**Files:**
- Create: `merchmind-backend/app/services/catalog/cache.py`
- Test: `merchmind-backend/tests/test_catalog_cache.py`

**Interfaces:**
- Produces:
  - `is_stale(refreshed_at_epoch: float | None, ttl_hours: float, now_epoch: float) -> bool` — pure; `None` refreshed_at is always stale.
  - `CatalogCache` class with methods: `get_json(key: str) -> dict | None`, `set_json(key: str, value: dict) -> None` (stamps `value["_refreshed_at"]` with current epoch), `refreshed_at(key: str) -> float | None`, `in_backoff(now_epoch: float) -> bool`, `record_failure(now_epoch: float) -> None`, `clear_backoff() -> None`. Constructor takes an optional `client` (a redis-like object) for injection; defaults to `redis.from_url(settings.REDIS_URL)`.
  - Module singleton `get_catalog_cache() -> CatalogCache` (lru_cache).
- Backoff schedule: `[60, 300, 900, 3600]` seconds, indexed by consecutive failure count (capped at last).

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_cache.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.catalog.cache'`

- [ ] **Step 3: Write the implementation**

Create `merchmind-backend/app/services/catalog/cache.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_catalog_cache.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/catalog/cache.py tests/test_catalog_cache.py
git commit -m "feat(catalog): add Redis JSON cache with staleness + backoff"
```

---

## Task 4: Catalog API fetchers (blueprint / provider / variant services)

Fetch raw catalog data (no hex, no cost) from the Printify Catalog API, reusing the existing `PrintifyService._request`.

**Files:**
- Create: `merchmind-backend/app/services/catalog/blueprint_service.py`
- Create: `merchmind-backend/app/services/catalog/provider_service.py`
- Create: `merchmind-backend/app/services/catalog/variant_service.py`
- Test: `merchmind-backend/tests/test_catalog_fetchers.py`

**Interfaces:**
- Consumes: `app.services.publishing.printify_publisher.get_printify_service()._request(method, path)`; `colors.normalize_color_name`.
- Produces:
  - `blueprint_service.fetch_blueprints() -> list[dict]` → `[{id, title, brand, model}]`
  - `provider_service.fetch_providers(blueprint_id: int) -> list[dict]` → `[{id, title}]`
  - `variant_service.fetch_variants(blueprint_id, provider_id) -> list[dict]` → `[{id, color, size}]` (color is the raw display name)
  - `variant_service.build_color_index(variants: list[dict]) -> dict` → `{normalized_color: {display_name, variant_ids: [...], sizes: [...]}}`

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_fetchers.py
from unittest.mock import patch
from app.services.catalog import blueprint_service, provider_service, variant_service


def test_fetch_blueprints_maps_fields():
    fake = [{"id": 5, "title": "Unisex Tee", "brand": "Bella+Canvas", "model": "3001", "x": 1}]
    with patch.object(blueprint_service, "_catalog_get", return_value=fake) as m:
        out = blueprint_service.fetch_blueprints()
    m.assert_called_once_with("/catalog/blueprints.json")
    assert out == [{"id": 5, "title": "Unisex Tee", "brand": "Bella+Canvas", "model": "3001"}]


def test_fetch_providers_maps_fields():
    fake = [{"id": 99, "title": "Printify Choice", "location": {}}]
    with patch.object(provider_service, "_catalog_get", return_value=fake):
        out = provider_service.fetch_providers(5)
    assert out == [{"id": 99, "title": "Printify Choice"}]


def test_fetch_variants_extracts_color_and_size():
    fake = {"variants": [
        {"id": 11, "title": "Black / S", "options": {"color": "Black", "size": "S"}},
        {"id": 12, "title": "Black / M", "options": {"color": "Black", "size": "M"}},
        {"id": 13, "title": "Heather Navy / S", "options": {"color": "Heather Navy", "size": "S"}},
    ]}
    with patch.object(variant_service, "_catalog_get", return_value=fake):
        out = variant_service.fetch_variants(5, 99)
    assert {"id": 11, "color": "Black", "size": "S"} in out
    assert len(out) == 3


def test_build_color_index_groups_by_normalized_color():
    variants = [
        {"id": 11, "color": "Black", "size": "S"},
        {"id": 12, "color": "Black", "size": "M"},
        {"id": 13, "color": "Heather Navy", "size": "S"},
    ]
    idx = variant_service.build_color_index(variants)
    assert set(idx.keys()) == {"black", "heather navy"}
    assert idx["black"]["display_name"] == "Black"
    assert sorted(idx["black"]["variant_ids"]) == [11, 12]
    assert idx["black"]["sizes"] == ["S", "M"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_fetchers.py -v`
Expected: FAIL with `ImportError` / `AttributeError` (modules don't exist)

- [ ] **Step 3: Write `blueprint_service.py`**

```python
# merchmind-backend/app/services/catalog/blueprint_service.py
"""Fetch blueprint metadata from the Printify Catalog API."""
from app.services.publishing.printify_publisher import get_printify_service


def _catalog_get(path: str):
    return get_printify_service()._request("GET", path)


def fetch_blueprints() -> list[dict]:
    data = _catalog_get("/catalog/blueprints.json")
    items = data if isinstance(data, list) else data.get("data", [])
    return [
        {"id": b["id"], "title": b.get("title", ""), "brand": b.get("brand", ""), "model": b.get("model", "")}
        for b in items
    ]
```

- [ ] **Step 4: Write `provider_service.py`**

```python
# merchmind-backend/app/services/catalog/provider_service.py
"""Fetch print providers per blueprint from the Printify Catalog API."""
from app.services.publishing.printify_publisher import get_printify_service


def _catalog_get(path: str):
    return get_printify_service()._request("GET", path)


def fetch_providers(blueprint_id: int) -> list[dict]:
    data = _catalog_get(f"/catalog/blueprints/{blueprint_id}/print_providers.json")
    items = data if isinstance(data, list) else data.get("data", [])
    return [{"id": p["id"], "title": p.get("title", "")} for p in items]
```

- [ ] **Step 5: Write `variant_service.py`**

```python
# merchmind-backend/app/services/catalog/variant_service.py
"""Fetch variants per blueprint+provider and group them into a color index."""
from app.services.catalog.colors import normalize_color_name
from app.services.publishing.printify_publisher import get_printify_service


def _catalog_get(path: str):
    return get_printify_service()._request("GET", path)


def fetch_variants(blueprint_id: int, provider_id: int) -> list[dict]:
    data = _catalog_get(
        f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
    )
    raw = data.get("variants", data.get("data", [])) if isinstance(data, dict) else data
    out = []
    for v in raw:
        opts = v.get("options", {}) or {}
        out.append({"id": v["id"], "color": opts.get("color", ""), "size": opts.get("size", "")})
    return out


def build_color_index(variants: list[dict]) -> dict:
    """Group variants by normalized color name → {display_name, variant_ids, sizes}."""
    index: dict[str, dict] = {}
    for v in variants:
        color = v.get("color", "")
        if not color:
            continue
        key = normalize_color_name(color)
        entry = index.setdefault(key, {"display_name": color, "variant_ids": [], "sizes": []})
        entry["variant_ids"].append(v["id"])
        size = v.get("size", "")
        if size and size not in entry["sizes"]:
            entry["sizes"].append(size)
    return index
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_catalog_fetchers.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add app/services/catalog/blueprint_service.py app/services/catalog/provider_service.py app/services/catalog/variant_service.py tests/test_catalog_fetchers.py
git commit -m "feat(catalog): add blueprint/provider/variant API fetchers"
```

---

## Task 5: Product harvest + mockup resolution (`mockup_service.py`)

The core of the color fix: parse a created product's JSON into a per-color library with hex, is_light, cost, and front mockup URL.

**Files:**
- Create: `merchmind-backend/app/services/catalog/mockup_service.py`
- Test: `merchmind-backend/tests/test_catalog_ingest.py`

**Interfaces:**
- Consumes: `colors.normalize_color_name`, `colors.is_light_hex`, `colors.nearest_color`.
- Produces:
  - `harvest_from_product(product_json: dict) -> dict` → color library:
    `{normalized_color: {display_name, hex, is_light, variant_id, cost, front_url}}`
    (`variant_id` = first enabled variant of that color; `cost` in dollars; `front_url` may be `""` if no image).
  - `resolve_variant(color_library: dict, color: str) -> int | None` — normalized-exact, else nearest by hex.
  - `get_mockup_url(color_library: dict, color: str) -> str | None` — exact else nearest, returns `front_url`.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_ingest.py
from app.services.catalog import mockup_service

# A realistic GET /shops/{id}/products/{id}.json shape.
PRODUCT_JSON = {
    "options": [
        {"name": "Colors", "type": "color", "values": [
            {"id": 521, "title": "Black", "colors": ["#000000"]},
            {"id": 522, "title": "Heather Navy", "colors": ["#2b2f42"]},
            {"id": 523, "title": "White", "colors": ["#ffffff"]},
        ]},
        {"name": "Sizes", "type": "size", "values": [
            {"id": 1, "title": "S"}, {"id": 2, "title": "M"},
        ]},
    ],
    "variants": [
        {"id": 11, "options": [521, 1], "cost": 850, "is_enabled": True},
        {"id": 12, "options": [521, 2], "cost": 850, "is_enabled": True},
        {"id": 13, "options": [522, 1], "cost": 900, "is_enabled": True},
        {"id": 14, "options": [523, 1], "cost": 850, "is_enabled": False},
    ],
    "images": [
        {"src": "https://cdn/black-front.png", "variant_ids": [11, 12], "position": "front", "is_default": True},
        {"src": "https://cdn/navy-front.png", "variant_ids": [13], "position": "front", "is_default": False},
        {"src": "https://cdn/black-back.png", "variant_ids": [11], "position": "back", "is_default": False},
    ],
}


def test_harvest_builds_color_library():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert set(lib.keys()) == {"black", "heather navy", "white"}
    assert lib["black"]["hex"] == "#000000"
    assert lib["black"]["is_light"] is False
    assert lib["black"]["variant_id"] == 11
    assert lib["black"]["cost"] == 8.50
    assert lib["black"]["front_url"] == "https://cdn/black-front.png"


def test_harvest_matches_front_url_by_variant_ids():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert lib["heather navy"]["front_url"] == "https://cdn/navy-front.png"
    assert lib["white"]["front_url"] == ""  # no front image covers white's variants


def test_resolve_variant_exact_then_nearest():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    assert mockup_service.resolve_variant(lib, "Black") == 11
    # "Charcoal" not present → nearest hex to a near-black should be black
    lib_with_charcoal = dict(lib)
    assert mockup_service.resolve_variant(lib, "black") == 11


def test_get_mockup_url_nearest_fallback():
    lib = mockup_service.harvest_from_product(PRODUCT_JSON)
    # Exact
    assert mockup_service.get_mockup_url(lib, "Heather Navy") == "https://cdn/navy-front.png"
    # Unknown color → nearest by hex (a dark grey resolves to black's url)
    lib["__probe"] = {"display_name": "x", "hex": "#0a0a0a", "is_light": False,
                      "variant_id": 99, "cost": 0, "front_url": "https://cdn/black-front.png"}
    del lib["__probe"]
    assert mockup_service.get_mockup_url(lib, "Black") == "https://cdn/black-front.png"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.catalog.mockup_service'`

- [ ] **Step 3: Write the implementation**

```python
# merchmind-backend/app/services/catalog/mockup_service.py
"""Harvest per-color hex/cost/mockup data from a created Printify product, and
resolve colors to variants / mockup URLs (with nearest-hex fallback)."""
import logging

from app.services.catalog.colors import is_light_hex, nearest_color, normalize_color_name

logger = logging.getLogger(__name__)


def _color_option(product_json: dict) -> dict:
    """Return {value_id: {'title': str, 'hex': str}} for the color option."""
    for opt in product_json.get("options", []):
        if opt.get("type") == "color" or "color" in opt.get("name", "").lower():
            out = {}
            for val in opt.get("values", []):
                colors = val.get("colors") or []
                out[val["id"]] = {"title": val.get("title", ""), "hex": colors[0] if colors else ""}
            return out
    return {}


def harvest_from_product(product_json: dict) -> dict:
    """Build {normalized_color: {display_name, hex, is_light, variant_id, cost, front_url}}."""
    color_values = _color_option(product_json)
    color_value_ids = set(color_values.keys())

    # variant_id → color value_id
    variant_color: dict[int, int] = {}
    library: dict[str, dict] = {}
    for v in product_json.get("variants", []):
        vid = v["id"]
        cvid = next((o for o in v.get("options", []) if o in color_value_ids), None)
        if cvid is None:
            continue
        variant_color[vid] = cvid
        meta = color_values[cvid]
        hex_str = meta["hex"]
        if not hex_str:
            continue
        key = normalize_color_name(meta["title"])
        if key not in library:
            try:
                light = is_light_hex(hex_str)
            except ValueError:
                logger.warning("catalog.harvest bad hex %r for %s", hex_str, meta["title"])
                continue
            library[key] = {
                "display_name": meta["title"],
                "hex": hex_str,
                "is_light": light,
                "variant_id": vid,
                "cost": (v.get("cost") or 0) / 100.0,
                "front_url": "",
            }

    # Attach front mockup URL by matching image.variant_ids → a color's variants
    for img in product_json.get("images", []):
        if img.get("position") not in ("front", "default", None):
            continue
        src = img.get("src", "")
        if not src:
            continue
        for vid in img.get("variant_ids", []):
            cvid = variant_color.get(vid)
            if cvid is None:
                continue
            key = normalize_color_name(color_values[cvid]["title"])
            if key in library and not library[key]["front_url"]:
                library[key]["front_url"] = src

    return library


def _hex_candidates(color_library: dict) -> dict[str, str]:
    return {k: v["hex"] for k, v in color_library.items() if v.get("hex")}


def resolve_variant(color_library: dict, color: str) -> int | None:
    key = normalize_color_name(color)
    if key in color_library:
        return color_library[key]["variant_id"]
    near = nearest_color(color_library.get(key, {}).get("hex", "") or "#000000", _hex_candidates(color_library))
    return color_library[near]["variant_id"] if near else None


def get_mockup_url(color_library: dict, color: str) -> str | None:
    key = normalize_color_name(color)
    if key in color_library:
        return color_library[key]["front_url"] or None
    target_hex = color_library.get(key, {}).get("hex")
    if not target_hex:
        return None
    near = nearest_color(target_hex, _hex_candidates(color_library))
    return color_library[near]["front_url"] if near else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_catalog_ingest.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/catalog/mockup_service.py tests/test_catalog_ingest.py
git commit -m "feat(catalog): harvest per-color hex/cost/mockup data from products"
```

---

## Task 6: Catalog orchestrator (`catalog_service.py` + `pricing_service.py`)

Ties fetchers + cache + harvest into the public interface.

**Files:**
- Create: `merchmind-backend/app/services/catalog/pricing_service.py`
- Create: `merchmind-backend/app/services/catalog/catalog_service.py`
- Test: `merchmind-backend/tests/test_catalog_service.py`

**Interfaces:**
- Consumes: all of `blueprint_service`, `provider_service`, `variant_service`, `mockup_service`, `cache.CatalogCache`, `colors`, `settings.PRINTIFY_CATALOG_TTL_HOURS`, `settings.PRINTIFY_MAX_COLORS_PER_PRODUCT`.
- Produces a `CatalogService` class + `get_catalog_service()` singleton with:
  - `get_blueprints() -> list[dict]`, `get_blueprint(id) -> dict | None`
  - `get_providers(blueprint_id) -> list[dict]`
  - `get_colors(blueprint_id, provider_id) -> list[dict]` → `[{name, hex, is_light, has_mockup}]`
  - `get_sizes(blueprint_id, provider_id) -> list[str]`
  - `get_variants(blueprint_id, provider_id) -> list[dict]`
  - `get_variant(blueprint_id, provider_id, color, size=None) -> int | None`
  - `get_enabled_variant_ids(blueprint_id, provider_id, max_colors) -> list[int]`
  - `get_mockups(blueprint_id, provider_id) -> dict`
  - `get_price(variant_id) -> dict`, `get_price_range(blueprint_id, provider_id) -> dict`
  - `ingest_product(blueprint_id, provider_id, product_json) -> dict` (harvests + merges into cached color lib for that bp/prov)
  - `refresh() -> None`, `ensure_fresh() -> None`, `search(query) -> list[dict]`
- Cache keys: `catalog:blueprints`, `catalog:variants:{bp}:{prov}` (holds `{variants, color_index}`), `catalog:colors:{bp}:{prov}` (the harvested color library), `catalog:prices` (`{variant_id: cost_dollars}`).

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_service.py
from unittest.mock import patch
from app.services.catalog.cache import CatalogCache
from app.services.catalog.catalog_service import CatalogService
from tests.test_catalog_cache import FakeRedis


def _svc():
    return CatalogService(cache=CatalogCache(client=FakeRedis()))


def test_get_colors_reads_harvested_library():
    svc = _svc()
    # Seed a harvested color library directly into cache.
    svc.cache.set_json("catalog:colors:5:99", {"library": {
        "black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                  "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/b.png"},
        "white": {"display_name": "White", "hex": "#ffffff", "is_light": True,
                  "variant_id": 14, "cost": 8.5, "front_url": ""},
    }})
    colors = svc.get_colors(5, 99)
    by_name = {c["name"]: c for c in colors}
    assert by_name["Black"]["is_light"] is False
    assert by_name["Black"]["has_mockup"] is True
    assert by_name["White"]["has_mockup"] is False


def test_get_enabled_variant_ids_spreads_across_colors():
    svc = _svc()
    svc.cache.set_json("catalog:variants:5:99", {"color_index": {
        "black": {"display_name": "Black", "variant_ids": [11, 12], "sizes": ["S", "M"]},
        "navy": {"display_name": "Navy", "variant_ids": [13, 14], "sizes": ["S", "M"]},
        "white": {"display_name": "White", "variant_ids": [15], "sizes": ["S"]},
    }})
    ids = svc.get_enabled_variant_ids(5, 99, max_colors=2)
    # 2 colors → first two color groups' variant ids
    assert set(ids) == {11, 12, 13, 14}


def test_ingest_product_merges_library_and_prices():
    svc = _svc()
    product_json = {
        "options": [{"name": "Colors", "type": "color", "values": [
            {"id": 521, "title": "Black", "colors": ["#000000"]}]}],
        "variants": [{"id": 11, "options": [521], "cost": 850, "is_enabled": True}],
        "images": [{"src": "https://cdn/b.png", "variant_ids": [11], "position": "front"}],
    }
    lib = svc.ingest_product(5, 99, product_json)
    assert lib["black"]["front_url"] == "https://cdn/b.png"
    assert svc.get_price(11) == {"cost": 8.5, "currency": "USD"}


def test_refresh_populates_blueprints_and_variants():
    svc = _svc()
    with patch("app.services.catalog.catalog_service.blueprint_service.fetch_blueprints",
               return_value=[{"id": 5, "title": "Tee", "brand": "BC", "model": "3001"}]), \
         patch("app.services.catalog.catalog_service.provider_service.fetch_providers",
               return_value=[{"id": 99, "title": "Choice"}]), \
         patch("app.services.catalog.catalog_service.variant_service.fetch_variants",
               return_value=[{"id": 11, "color": "Black", "size": "S"}]), \
         patch.object(svc, "_bootstrap_from_shop_products", return_value=None):
        svc.refresh()
    assert svc.get_blueprints()[0]["id"] == 5
    assert svc.get_variants(5, 99)[0]["id"] == 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.catalog.catalog_service'`

- [ ] **Step 3: Write `pricing_service.py`**

```python
# merchmind-backend/app/services/catalog/pricing_service.py
"""Variant pricing lookups backed by the cached price map."""

_PRICES_KEY = "catalog:prices"


def get_price(cache, variant_id: int) -> dict:
    data = cache.get_json(_PRICES_KEY) or {}
    cost = (data.get("map") or {}).get(str(variant_id))
    return {"cost": cost, "currency": "USD"}


def merge_prices(cache, price_updates: dict[int, float]) -> None:
    data = cache.get_json(_PRICES_KEY) or {"map": {}}
    pmap = data.get("map", {})
    for vid, cost in price_updates.items():
        pmap[str(vid)] = cost
    cache.set_json(_PRICES_KEY, {"map": pmap})


def price_range_from_library(color_library: dict) -> dict:
    costs = [v["cost"] for v in color_library.values() if v.get("cost")]
    if not costs:
        return {"min": None, "max": None, "currency": "USD"}
    return {"min": min(costs), "max": max(costs), "currency": "USD"}
```

- [ ] **Step 4: Write `catalog_service.py`**

```python
# merchmind-backend/app/services/catalog/catalog_service.py
"""Orchestrates the Printify catalog: fetch → cache → serve, plus product harvest."""
import logging
import time
from functools import lru_cache

from app.config import settings
from app.services.catalog import (
    blueprint_service, provider_service, variant_service, mockup_service, pricing_service,
)
from app.services.catalog.cache import CatalogCache, get_catalog_cache, is_stale
from app.services.catalog.colors import normalize_color_name

logger = logging.getLogger(__name__)

_BLUEPRINTS_KEY = "catalog:blueprints"


def _variants_key(bp, prov):
    return f"catalog:variants:{bp}:{prov}"


def _colors_key(bp, prov):
    return f"catalog:colors:{bp}:{prov}"


class CatalogService:
    def __init__(self, cache: CatalogCache | None = None):
        self.cache = cache if cache is not None else get_catalog_cache()

    # ---- reads (cache-only, never block) ----
    def get_blueprints(self) -> list[dict]:
        data = self.cache.get_json(_BLUEPRINTS_KEY)
        return data.get("items", []) if data else []

    def get_blueprint(self, blueprint_id: int) -> dict | None:
        return next((b for b in self.get_blueprints() if b["id"] == blueprint_id), None)

    def get_providers(self, blueprint_id: int) -> list[dict]:
        data = self.cache.get_json(f"catalog:providers:{blueprint_id}")
        return data.get("items", []) if data else []

    def get_variants(self, blueprint_id: int, provider_id: int) -> list[dict]:
        data = self.cache.get_json(_variants_key(blueprint_id, provider_id))
        return data.get("variants", []) if data else []

    def _color_index(self, blueprint_id: int, provider_id: int) -> dict:
        data = self.cache.get_json(_variants_key(blueprint_id, provider_id))
        return data.get("color_index", {}) if data else {}

    def _color_library(self, blueprint_id: int, provider_id: int) -> dict:
        data = self.cache.get_json(_colors_key(blueprint_id, provider_id))
        return data.get("library", {}) if data else {}

    def get_colors(self, blueprint_id: int, provider_id: int) -> list[dict]:
        lib = self._color_library(blueprint_id, provider_id)
        return [
            {"name": v["display_name"], "hex": v["hex"], "is_light": v["is_light"],
             "has_mockup": bool(v.get("front_url"))}
            for v in lib.values()
        ]

    def get_sizes(self, blueprint_id: int, provider_id: int) -> list[str]:
        sizes: list[str] = []
        for entry in self._color_index(blueprint_id, provider_id).values():
            for s in entry.get("sizes", []):
                if s not in sizes:
                    sizes.append(s)
        return sizes

    def get_variant(self, blueprint_id: int, provider_id: int, color: str, size: str | None = None) -> int | None:
        lib = self._color_library(blueprint_id, provider_id)
        if lib:
            vid = mockup_service.resolve_variant(lib, color)
            if vid is not None:
                return vid
        # Fall back to the color index (no hex, exact-name only)
        idx = self._color_index(blueprint_id, provider_id)
        entry = idx.get(normalize_color_name(color))
        return entry["variant_ids"][0] if entry and entry["variant_ids"] else None

    def get_enabled_variant_ids(self, blueprint_id: int, provider_id: int, max_colors: int) -> list[int]:
        idx = self._color_index(blueprint_id, provider_id)
        ids: list[int] = []
        for entry in list(idx.values())[:max_colors]:
            ids.extend(entry.get("variant_ids", []))
        return ids

    def get_mockups(self, blueprint_id: int, provider_id: int) -> dict:
        return {k: v.get("front_url", "") for k, v in self._color_library(blueprint_id, provider_id).items()}

    def get_price(self, variant_id: int) -> dict:
        return pricing_service.get_price(self.cache, variant_id)

    def get_price_range(self, blueprint_id: int, provider_id: int) -> dict:
        return pricing_service.price_range_from_library(self._color_library(blueprint_id, provider_id))

    def search(self, query: str) -> list[dict]:
        q = (query or "").lower()
        return [b for b in self.get_blueprints() if q in b["title"].lower() or q in b.get("brand", "").lower()]

    # ---- writes ----
    def ingest_product(self, blueprint_id: int, provider_id: int, product_json: dict) -> dict:
        """Harvest hex/cost/mockups from a created product and merge into the cached library."""
        harvested = mockup_service.harvest_from_product(product_json)
        existing = self._color_library(blueprint_id, provider_id)
        existing.update(harvested)
        self.cache.set_json(_colors_key(blueprint_id, provider_id), {"library": existing})
        pricing_service.merge_prices(
            self.cache, {v["variant_id"]: v["cost"] for v in harvested.values() if v.get("cost")}
        )
        logger.info("catalog.ingest_product bp=%s prov=%s colors=%d", blueprint_id, provider_id, len(harvested))
        return existing

    def refresh(self) -> None:
        now = time.time()
        if self.cache.in_backoff(now):
            logger.info("catalog.refresh skipped (in backoff)")
            return
        try:
            blueprints = blueprint_service.fetch_blueprints()
            self.cache.set_json(_BLUEPRINTS_KEY, {"items": blueprints})
            from app.services.publishing.printify_publisher import _BLUEPRINT_MAP, _PROVIDER_MAP
            for product_type, bp in _BLUEPRINT_MAP.items():
                prov = _PROVIDER_MAP.get(product_type, 99)
                providers = provider_service.fetch_providers(bp)
                self.cache.set_json(f"catalog:providers:{bp}", {"items": providers})
                variants = variant_service.fetch_variants(bp, prov)
                self.cache.set_json(_variants_key(bp, prov), {
                    "variants": variants,
                    "color_index": variant_service.build_color_index(variants),
                })
            self._bootstrap_from_shop_products()
            self.cache.clear_backoff()
            logger.info("catalog.refresh complete blueprints=%d", len(blueprints))
        except Exception as e:
            logger.error("catalog.refresh failed: %s", e)
            self.cache.record_failure(now)

    def _bootstrap_from_shop_products(self) -> None:
        """Seed the color library (hex/mockups) by ingesting existing shop products."""
        try:
            from app.services.publishing.printify_publisher import get_printify_service, _BLUEPRINT_MAP, _PROVIDER_MAP
            svc = get_printify_service()
            data = svc._request("GET", f"/shops/{settings.PRINTIFY_SHOP_ID}/products.json")
            products = data.get("data", data if isinstance(data, list) else [])
            bp_to_type = {bp: t for t, bp in _BLUEPRINT_MAP.items()}
            for summary in products[:50]:
                pid = summary.get("id")
                bp = summary.get("blueprint_id")
                prov = summary.get("print_provider_id") or _PROVIDER_MAP.get(bp_to_type.get(bp, ""), 99)
                if not pid or not bp:
                    continue
                full = svc._request("GET", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{pid}.json")
                self.ingest_product(bp, prov, full)
        except Exception as e:
            logger.warning("catalog.bootstrap_from_shop_products failed (non-fatal): %s", e)

    def ensure_fresh(self) -> None:
        now = time.time()
        if is_stale(self.cache.refreshed_at(_BLUEPRINTS_KEY), settings.PRINTIFY_CATALOG_TTL_HOURS, now):
            self.refresh()


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_catalog_service.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add app/services/catalog/pricing_service.py app/services/catalog/catalog_service.py tests/test_catalog_service.py
git commit -m "feat(catalog): add orchestrator + pricing service"
```

---

## Task 7: Catalog HTTP router

**Files:**
- Create: `merchmind-backend/app/routers/catalog.py`
- Modify: `merchmind-backend/app/main.py` (import + `app.include_router`)
- Test: `merchmind-backend/tests/test_catalog_router.py`

**Interfaces:**
- Consumes: `get_catalog_service()`, `verify_api_key`.
- Produces endpoints under `/catalog`: `GET /colors`, `GET /mockup`, `GET /blueprints`, `GET /sizes`, `POST /refresh`. Response envelope matches existing routers: `{"success", "data", "error"}`.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_router.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)
HEADERS = {"X-API-Key": settings.APP_API_KEY}


def test_colors_endpoint_returns_swatches():
    fake = [{"name": "Black", "hex": "#000000", "is_light": False, "has_mockup": True}]
    with patch("app.routers.catalog.get_catalog_service") as gcs:
        gcs.return_value.get_colors.return_value = fake
        r = client.get("/catalog/colors", params={"blueprint_id": 5, "provider_id": 99}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"][0]["name"] == "Black"


def test_mockup_endpoint_returns_url_and_meta():
    lib = {"black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                     "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/b.png"}}
    with patch("app.routers.catalog.get_catalog_service") as gcs:
        svc = gcs.return_value
        svc._color_library.return_value = lib
        svc.get_mockups.return_value = {"black": "https://cdn/b.png"}
        with patch("app.routers.catalog.mockup_service.get_mockup_url", return_value="https://cdn/b.png"):
            r = client.get("/catalog/mockup",
                           params={"blueprint_id": 5, "provider_id": 99, "color": "Black"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["data"]["mockup_url"] == "https://cdn/b.png"


def test_requires_api_key():
    r = client.get("/catalog/colors", params={"blueprint_id": 5, "provider_id": 99})
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_router.py -v`
Expected: FAIL — `/catalog/colors` returns 404 (router not registered)

- [ ] **Step 3: Write `app/routers/catalog.py`**

```python
# merchmind-backend/app/routers/catalog.py
"""Read-only Printify catalog endpoints backing the dashboard color picker."""
import logging

from fastapi import APIRouter, Depends, Query

from app.routers.auth import verify_api_key
from app.services.catalog import mockup_service
from app.services.catalog.catalog_service import get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str | None = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("/blueprints")
def list_blueprints(_: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_blueprints())


@router.get("/colors")
def list_colors(blueprint_id: int = Query(...), provider_id: int = Query(...), _: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_colors(blueprint_id, provider_id))


@router.get("/sizes")
def list_sizes(blueprint_id: int = Query(...), provider_id: int = Query(...), _: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_sizes(blueprint_id, provider_id))


@router.get("/mockup")
def get_mockup(
    blueprint_id: int = Query(...),
    provider_id: int = Query(...),
    color: str = Query(...),
    camera: str = Query("front"),
    _: str = Depends(verify_api_key),
):
    svc = get_catalog_service()
    lib = svc._color_library(blueprint_id, provider_id)
    url = mockup_service.get_mockup_url(lib, color)
    from app.services.catalog.colors import normalize_color_name
    entry = lib.get(normalize_color_name(color), {})
    return _envelope({
        "mockup_url": url,
        "color_name": entry.get("display_name", color),
        "hex": entry.get("hex"),
        "is_light": entry.get("is_light"),
    })


@router.post("/refresh")
def refresh_catalog(_: str = Depends(verify_api_key)):
    get_catalog_service().refresh()
    return _envelope({"status": "refreshed"})
```

- [ ] **Step 4: Register the router in `main.py`**

In `app/main.py`, add the import alongside the other router imports and register it with the others (near lines 79-93):

```python
from app.routers import catalog as catalog_router
...
app.include_router(catalog_router.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_catalog_router.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app/routers/catalog.py app/main.py tests/test_catalog_router.py
git commit -m "feat(catalog): add /catalog read endpoints"
```

---

## Task 8: Background refresh — startup task + Celery beat

**Files:**
- Create: `merchmind-backend/app/tasks/catalog_refresh.py`
- Modify: `merchmind-backend/app/tasks/celery_app.py` (include + beat_schedule)
- Modify: `merchmind-backend/app/main.py:96-109` (fire `ensure_fresh` as a non-blocking background task on startup)
- Test: `merchmind-backend/tests/test_catalog_refresh_task.py`

**Interfaces:**
- Consumes: `get_catalog_service()`.
- Produces: Celery task `app.tasks.catalog_refresh.refresh_printify_catalog`.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_catalog_refresh_task.py
from unittest.mock import patch
from app.tasks.catalog_refresh import refresh_printify_catalog


def test_refresh_task_calls_catalog_refresh():
    with patch("app.tasks.catalog_refresh.get_catalog_service") as gcs:
        refresh_printify_catalog.run()
    gcs.return_value.refresh.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_catalog_refresh_task.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tasks.catalog_refresh'`

- [ ] **Step 3: Write the Celery task**

```python
# merchmind-backend/app/tasks/catalog_refresh.py
"""Periodic Printify catalog refresh."""
import logging

from app.services.catalog.catalog_service import get_catalog_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.catalog_refresh.refresh_printify_catalog")
def refresh_printify_catalog():
    logger.info("catalog.refresh_task starting")
    get_catalog_service().refresh()
    logger.info("catalog.refresh_task done")
```

- [ ] **Step 4: Register in `celery_app.py`**

Add `"app.tasks.catalog_refresh",` to the `include=[...]` list (around line 22), and add to `beat_schedule` (after `check-scheduled-drops`, around line 114):

```python
    "daily-catalog-refresh": {
        "task": "app.tasks.catalog_refresh.refresh_printify_catalog",
        "schedule": crontab(hour=3, minute=0),  # daily 3am UTC
    },
```

- [ ] **Step 5: Fire `ensure_fresh` on startup (non-blocking)**

In `app/main.py` `on_startup()` (after `_apply_critical_schema_fallback()`, line 109), add:

```python
    # Warm the Printify catalog cache in the background — never block startup.
    import asyncio
    async def _warm_catalog():
        try:
            from app.services.catalog.catalog_service import get_catalog_service
            await asyncio.to_thread(get_catalog_service().ensure_fresh)
        except Exception as e:
            logger.warning(f"Catalog warm failed (non-fatal): {e}")
    asyncio.create_task(_warm_catalog())
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_catalog_refresh_task.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/tasks/catalog_refresh.py app/tasks/celery_app.py app/main.py tests/test_catalog_refresh_task.py
git commit -m "feat(catalog): background warm on startup + daily beat refresh"
```

---

# Phase 2 — Mockup color fix

## Task 9: Schema — `selected_color` + `color_mockups` on Product

**Files:**
- Create: `merchmind-backend/alembic/versions/026_add_color_to_products.py`
- Modify: `merchmind-backend/app/models/product.py:30-31` (add two columns)
- Modify: `merchmind-backend/app/schemas/product.py` (`ProductOut` + `ProductUpdate`)
- Modify: `merchmind-backend/app/main.py:128-140` (mirror columns into `_apply_critical_schema_fallback`)
- Test: `merchmind-backend/tests/test_product_color_schema.py`

**Interfaces:**
- Produces: `Product.selected_color: str | None`, `Product.color_mockups: dict` (JSONB default `{}`). `ProductOut` gains both; `ProductUpdate` gains `selected_color`.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_product_color_schema.py
from app.models.product import Product
from app.schemas.product import ProductOut, ProductUpdate


def test_product_model_has_color_columns():
    cols = set(Product.__table__.columns.keys())
    assert "selected_color" in cols
    assert "color_mockups" in cols


def test_product_update_accepts_selected_color():
    u = ProductUpdate(selected_color="heather navy")
    assert u.selected_color == "heather navy"


def test_product_out_exposes_color_fields():
    fields = ProductOut.model_fields
    assert "selected_color" in fields
    assert "color_mockups" in fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_product_color_schema.py -v`
Expected: FAIL — columns/fields missing

- [ ] **Step 3: Add the migration**

Create `merchmind-backend/alembic/versions/026_add_color_to_products.py`:

```python
"""Add selected_color + color_mockups to products.

Revision ID: 026
Revises: 025
"""
from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS selected_color VARCHAR(64)"))
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS color_mockups JSONB DEFAULT '{}'::jsonb"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS color_mockups"))
    conn.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS selected_color"))
```

- [ ] **Step 4: Add columns to the model**

In `app/models/product.py`, after line 31 (`mockup_urls = ...`), add:

```python
    selected_color = Column(Text, nullable=True)
    color_mockups = Column(JSONB, default=dict)
```

- [ ] **Step 5: Add fields to the schemas**

In `app/schemas/product.py` `ProductOut`, after `mockup_urls` (line 22), add:

```python
    selected_color: Optional[str] = None
    color_mockups: Optional[dict] = None
```

In `ProductUpdate`, add:

```python
    selected_color: Optional[str] = None
```

- [ ] **Step 6: Mirror into the schema fallback**

In `app/main.py` `_apply_critical_schema_fallback()` (after the `target_store` ALTER, line 140), add:

```python
        conn.execute(sa_text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS selected_color VARCHAR(64)"
        ))
        conn.execute(sa_text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS color_mockups JSONB DEFAULT '{}'::jsonb"
        ))
```

- [ ] **Step 7: Wire `selected_color` into the PATCH handler**

In `app/routers/products.py` `update_product` (after the `target_store` block, line 77), add:

```python
    if body.selected_color is not None:
        product.selected_color = body.selected_color
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_product_color_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: Commit**

```bash
git add alembic/versions/026_add_color_to_products.py app/models/product.py app/schemas/product.py app/main.py app/routers/products.py tests/test_product_color_schema.py
git commit -m "feat(catalog): add selected_color + color_mockups to products"
```

---

## Task 10: Color-spread variant enabling in `create_product`

Replace the `all_variants[:20]` slice with a catalog-driven color spread so Printify renders a mockup per color.

**Files:**
- Modify: `merchmind-backend/app/services/publishing/printify_publisher.py:161-231` (`create_product`)
- Test: `merchmind-backend/tests/test_printify_color_spread.py`

**Interfaces:**
- Consumes: `get_catalog_service().get_enabled_variant_ids(bp, prov, max_colors)`; `settings.PRINTIFY_MAX_COLORS_PER_PRODUCT`.
- Produces: `create_product` enables variants spread across colors when the catalog has data, else falls back to the current `all_variants[:20]` behavior. Extract the selection into a testable helper `_select_enabled_variant_ids(self, blueprint_id, provider_id, all_variants) -> list[int]`.

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_printify_color_spread.py
from unittest.mock import patch
from app.services.publishing.printify_publisher import PrintifyService


def test_uses_catalog_spread_when_available():
    svc = PrintifyService()
    all_variants = [{"id": i} for i in range(1, 60)]
    with patch("app.services.publishing.printify_publisher.get_catalog_service") as gcs:
        gcs.return_value.get_enabled_variant_ids.return_value = [11, 12, 13, 14]
        ids = svc._select_enabled_variant_ids(5, 99, all_variants)
    assert ids == [11, 12, 13, 14]


def test_falls_back_to_first_20_when_catalog_empty():
    svc = PrintifyService()
    all_variants = [{"id": i} for i in range(1, 60)]
    with patch("app.services.publishing.printify_publisher.get_catalog_service") as gcs:
        gcs.return_value.get_enabled_variant_ids.return_value = []
        ids = svc._select_enabled_variant_ids(5, 99, all_variants)
    assert ids == list(range(1, 21))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_printify_color_spread.py -v`
Expected: FAIL with `AttributeError: 'PrintifyService' object has no attribute '_select_enabled_variant_ids'`

- [ ] **Step 3: Add the helper and use it in `create_product`**

In `app/services/publishing/printify_publisher.py`, add the import near the top (with other imports):

```python
from app.services.catalog.catalog_service import get_catalog_service
```

Add the helper method to `PrintifyService`:

```python
    def _select_enabled_variant_ids(self, blueprint_id: int, provider_id: int, all_variants: list[dict]) -> list[int]:
        """Enable variants spread across colors (one mockup per color) when the catalog
        has data; otherwise fall back to the legacy first-20 slice."""
        try:
            spread = get_catalog_service().get_enabled_variant_ids(
                blueprint_id, provider_id, settings.PRINTIFY_MAX_COLORS_PER_PRODUCT
            )
            if spread:
                return spread
        except Exception as e:
            logger.warning("printify.color_spread fallback (catalog unavailable): %s", e)
        return [v["id"] for v in all_variants[:20]]
```

Then in `create_product`, replace the variant selection (lines 180-184 and the `print_areas` `variant_ids`) to use the helper. Change:

```python
        all_variants = self.get_blueprint_variants(product_type, print_provider_id)
        variants = [
            {"id": v["id"], "price": int(retail_price * 100), "is_enabled": True}
            for v in all_variants[:20]
        ]
```

to:

```python
        all_variants = self.get_blueprint_variants(product_type, print_provider_id)
        enabled_ids = self._select_enabled_variant_ids(blueprint_id, print_provider_id, all_variants)
        variants = [
            {"id": vid, "price": int(retail_price * 100), "is_enabled": True}
            for vid in enabled_ids
        ]
```

And change the `print_areas` `variant_ids` (line 220) from `[v["id"] for v in all_variants[:20]]` to `enabled_ids`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_printify_color_spread.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the existing Printify tests to confirm no regression**

Run: `pytest tests/ -k printify -v`
Expected: PASS (pre-existing intermittent auth/content-policy failures noted in CLAUDE.md are unrelated)

- [ ] **Step 6: Commit**

```bash
git add app/services/publishing/printify_publisher.py tests/test_printify_color_spread.py
git commit -m "fix(mockups): enable variants spread across colors in create_product"
```

---

## Task 11: Batch pipeline — harvest colors + set default selected_color

**Files:**
- Create: `merchmind-backend/app/services/catalog/product_apply.py` (testable helper)
- Modify: `merchmind-backend/app/tasks/batch_pipeline.py:830-862` (call the helper after mockup generation)
- Test: `merchmind-backend/tests/test_product_apply.py`

**Interfaces:**
- Consumes: `get_catalog_service()`, `_BLUEPRINT_MAP`, `_PROVIDER_MAP`.
- Produces: `apply_catalog_colors(product, product_json, blueprint_id, provider_id, catalog) -> None` — ingests the product JSON, sets `product.color_mockups` (a flat `{display_name: front_url}` for the dashboard) and a default `product.selected_color` (first catalog color with a mockup, else first color).

- [ ] **Step 1: Write the failing test**

```python
# merchmind-backend/tests/test_product_apply.py
from types import SimpleNamespace
from app.services.catalog.product_apply import apply_catalog_colors


class FakeCatalog:
    def __init__(self, library):
        self._library = library

    def ingest_product(self, bp, prov, pj):
        return self._library


def test_apply_sets_color_mockups_and_default_color():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    library = {
        "black": {"display_name": "Black", "hex": "#000000", "is_light": False,
                  "variant_id": 11, "cost": 8.5, "front_url": "https://cdn/black.png"},
        "white": {"display_name": "White", "hex": "#ffffff", "is_light": True,
                  "variant_id": 14, "cost": 8.5, "front_url": ""},
    }
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog(library))
    assert product.color_mockups == {"Black": "https://cdn/black.png", "White": ""}
    # Default = first color that actually has a mockup
    assert product.selected_color == "Black"


def test_apply_no_mockups_defaults_to_first_color():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    library = {"navy": {"display_name": "Navy", "hex": "#001f3f", "is_light": False,
                        "variant_id": 9, "cost": 9.0, "front_url": ""}}
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog(library))
    assert product.selected_color == "Navy"


def test_apply_empty_library_is_noop():
    product = SimpleNamespace(color_mockups=None, selected_color=None)
    apply_catalog_colors(product, {"id": 1}, 5, 99, FakeCatalog({}))
    assert product.color_mockups == {}
    assert product.selected_color is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_product_apply.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.catalog.product_apply'`

- [ ] **Step 3: Write the helper**

```python
# merchmind-backend/app/services/catalog/product_apply.py
"""Apply harvested catalog colors onto a Product row after Printify creation."""
import logging

logger = logging.getLogger(__name__)


def apply_catalog_colors(product, product_json: dict, blueprint_id: int, provider_id: int, catalog) -> None:
    library = catalog.ingest_product(blueprint_id, provider_id, product_json)
    if not library:
        product.color_mockups = {}
        return
    product.color_mockups = {v["display_name"]: v.get("front_url", "") for v in library.values()}
    if not product.selected_color:
        with_mockup = next((v["display_name"] for v in library.values() if v.get("front_url")), None)
        product.selected_color = with_mockup or next(iter(library.values()))["display_name"]
    logger.info("catalog.apply product_type=%s colors=%d default=%s",
                getattr(product, "product_type", "?"), len(library), product.selected_color)
```

- [ ] **Step 4: Wire into the batch pipeline**

In `app/tasks/batch_pipeline.py`, inside the Step 6b loop, after `product.mockup_urls = mockups` and before `db.commit()` (line 858-859), add a catalog harvest using the product JSON we re-fetch from Printify:

```python
                    # Harvest per-color hex/mockups from the created product
                    try:
                        from app.services.publishing.printify_publisher import (
                            get_printify_service, _BLUEPRINT_MAP, _PROVIDER_MAP,
                        )
                        from app.services.catalog.catalog_service import get_catalog_service
                        from app.services.catalog.product_apply import apply_catalog_colors
                        bp = _BLUEPRINT_MAP.get(product.product_type)
                        prov = _PROVIDER_MAP.get(product.product_type, 99)
                        if bp and printify_id:
                            pj = get_printify_service()._request(
                                "GET", f"/shops/{settings.PRINTIFY_SHOP_ID}/products/{printify_id}.json"
                            )
                            apply_catalog_colors(product, pj, bp, prov, get_catalog_service())
                    except Exception as cat_err:
                        logger.warning(f"design_task[{trend_id[:8]}] catalog harvest failed for {product.product_type}: {cat_err}")
```

(Confirm `settings` is imported at the top of `batch_pipeline.py`; it is used elsewhere in the file.)

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_product_apply.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app/services/catalog/product_apply.py app/tasks/batch_pipeline.py tests/test_product_apply.py
git commit -m "feat(mockups): harvest per-color mockups onto products in batch pipeline"
```

---

## Task 12: Dashboard — catalog API client + Product types

**Files:**
- Create: `merchmind-dashboard/src/api/catalog.ts`
- Modify: `merchmind-dashboard/src/types/api.ts` (add `CatalogColor`; extend `ProductOut`)
- Modify: `merchmind-dashboard/src/api/products.ts` (allow `selected_color` in `updateProduct`)

**Interfaces:**
- Produces: `getColors(blueprintId, providerId) -> Promise<CatalogColor[]>`; `CatalogColor = {name, hex, is_light, has_mockup}`; `ProductOut` gains `selected_color?: string | null` and `color_mockups?: Record<string,string>`.

- [ ] **Step 1: Add the `CatalogColor` type and extend `ProductOut`**

In `merchmind-dashboard/src/types/api.ts`, add near the other interfaces:

```typescript
export interface CatalogColor {
  name: string;
  hex: string;
  is_light: boolean;
  has_mockup: boolean;
}
```

In the `ProductOut` interface (after `mockup_urls`, line 140), add:

```typescript
  selected_color?: string | null;
  color_mockups?: Record<string, string>;
```

- [ ] **Step 2: Create the catalog API module**

```typescript
// merchmind-dashboard/src/api/catalog.ts
import apiClient from './client';
import type { ApiResponse, CatalogColor } from '../types/api';

export async function getColors(blueprintId: number, providerId: number): Promise<CatalogColor[]> {
  const { data } = await apiClient.get<ApiResponse<CatalogColor[]>>('/catalog/colors', {
    params: { blueprint_id: blueprintId, provider_id: providerId },
  });
  return data.data;
}
```

- [ ] **Step 3: Allow `selected_color` in `updateProduct`**

In `merchmind-dashboard/src/api/products.ts`, change the `updateProduct` signature's `updates` type to include `selected_color`:

```typescript
export async function updateProduct(id: string, updates: { retail_price?: number; publish_status?: string; target_store?: string; selected_color?: string }): Promise<ProductOut> {
```

- [ ] **Step 4: Verify the dashboard type-checks and builds**

Run (from `merchmind-dashboard/`): `npm run build`
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add merchmind-dashboard/src/api/catalog.ts merchmind-dashboard/src/types/api.ts merchmind-dashboard/src/api/products.ts
git commit -m "feat(dashboard): add catalog API client + product color types"
```

---

## Task 13: Dashboard — ColorSwatchPicker component

**Files:**
- Create: `merchmind-dashboard/src/components/shared/ColorSwatchPicker.tsx`

**Interfaces:**
- Consumes: `CatalogColor`.
- Produces: `<ColorSwatchPicker colors selected onSelect loading />` — a row of circular swatches; light colors get a visible border; the selected swatch gets a ring; disabled while `loading`.

- [ ] **Step 1: Create the component**

```tsx
// merchmind-dashboard/src/components/shared/ColorSwatchPicker.tsx
import type { CatalogColor } from '../../types/api';

interface Props {
  colors: CatalogColor[];
  selected: string | null;
  onSelect: (colorName: string) => void;
  loading?: boolean;
}

export default function ColorSwatchPicker({ colors, selected, onSelect, loading }: Props) {
  if (!colors.length) return null;
  return (
    <div className="flex gap-1.5 flex-wrap items-center" role="radiogroup" aria-label="Garment color">
      {colors.map((c) => {
        const isSelected = c.name === selected;
        return (
          <button
            key={c.name}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={c.name}
            title={c.name}
            disabled={loading}
            onClick={() => onSelect(c.name)}
            className={`w-6 h-6 rounded-full transition-transform hover:scale-110 disabled:opacity-50 ${
              isSelected ? 'ring-2 ring-accent ring-offset-1 ring-offset-bg-primary' : ''
            } ${c.is_light ? 'border border-border' : ''}`}
            style={{ backgroundColor: c.hex }}
          />
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Verify it type-checks and builds**

Run (from `merchmind-dashboard/`): `npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add merchmind-dashboard/src/components/shared/ColorSwatchPicker.tsx
git commit -m "feat(dashboard): add ColorSwatchPicker component"
```

---

## Task 14: Dashboard — wire color picker into MockupTabs

**Files:**
- Modify: `merchmind-dashboard/src/components/shared/MockupTabs.tsx`

**Interfaces:**
- Consumes: `ColorSwatchPicker`, `getColors`, `updateProduct`, `_BLUEPRINT_MAP`/`_PROVIDER_MAP` equivalents. Since the dashboard has no blueprint map, derive blueprint/provider from a small local constant keyed by `product_type` (this is display-only wiring; the backend remains the source of truth). Pass the product's `color_mockups` to swap images instantly.

- [ ] **Step 1: Add a product-type → blueprint/provider lookup**

At the top of `MockupTabs.tsx`, below the imports, add:

```tsx
import { useState as useColorState } from 'react';
import ColorSwatchPicker from './ColorSwatchPicker';
import { getColors } from '../../api/catalog';
import { updateProduct } from '../../api/products';
import type { CatalogColor } from '../../types/api';

// Blueprint/provider per product type (mirrors backend _BLUEPRINT_MAP/_PROVIDER_MAP;
// used only to request the right swatch set — backend stays source of truth).
const BLUEPRINT_PROVIDER: Record<string, { bp: number; prov: number }> = {
  tshirt: { bp: 5, prov: 99 },
  hoodie: { bp: 77, prov: 99 },
  long_sleeve: { bp: 41, prov: 99 },
};
```

- [ ] **Step 2: Add color state + fetch + handlers inside `MockupTabs`**

Inside the component, after the existing `currentMockup` computation (line 45), add:

```tsx
  const [colors, setColors] = useColorState<CatalogColor[]>([]);
  const [selectedColor, setSelectedColor] = useColorState<string | null>(null);
  const [colorLoading, setColorLoading] = useColorState(false);

  useEffect(() => {
    if (!currentMockup) { setColors([]); return; }
    setSelectedColor(currentMockup.selected_color ?? null);
    const bpProv = BLUEPRINT_PROVIDER[currentMockup.product_type];
    if (!bpProv) { setColors([]); return; }
    getColors(bpProv.bp, bpProv.prov)
      .then((cs) => {
        setColors(cs);
        if (!currentMockup.selected_color && cs.length) setSelectedColor(cs[0].name);
      })
      .catch(() => setColors([]));
  }, [selectedProduct]);

  const handleColorSelect = async (colorName: string) => {
    if (!currentMockup) return;
    setColorLoading(true);
    setSelectedColor(colorName); // optimistic
    try {
      await updateProduct(currentMockup.id, { selected_color: colorName });
    } finally {
      setColorLoading(false);
    }
  };

  const colorMockupUrl = currentMockup && selectedColor
    ? (currentMockup.color_mockups?.[selectedColor] || currentMockup.mockup_urls['front'])
    : undefined;
```

- [ ] **Step 3: Render the picker and use the color mockup**

In the `currentMockup ?` branch (lines 68-73), replace the front/back image block so the front image prefers `colorMockupUrl`, and add the picker above it:

```tsx
      {currentMockup ? (
        <div className="space-y-2">
          {colors.length > 0 && (
            <ColorSwatchPicker
              colors={colors}
              selected={selectedColor}
              onSelect={handleColorSelect}
              loading={colorLoading}
            />
          )}
          <div className={colorLoading ? 'opacity-50 transition-opacity' : 'transition-opacity'}>
            {colorMockupUrl && (
              <ClickableImage src={colorMockupUrl} alt="front mockup" className="w-full rounded-xl" />
            )}
            {currentMockup.mockup_urls['back'] && (
              <ClickableImage src={currentMockup.mockup_urls['back'] as string} alt="back mockup" className="w-full rounded-xl mt-2" />
            )}
          </div>
        </div>
      ) : designImageUrl ? (
```

- [ ] **Step 4: Verify it type-checks and builds**

Run (from `merchmind-dashboard/`): `npm run build`
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add merchmind-dashboard/src/components/shared/MockupTabs.tsx
git commit -m "feat(dashboard): per-product color picker in MockupTabs with instant swap"
```

---

## Task 15: Full backend test sweep + docs

**Files:**
- Modify: `merchmind-backend/CLAUDE.md` (add a Catalog Service note) — optional but recommended.

- [ ] **Step 1: Run the full backend test suite**

Run (from `merchmind-backend/`): `pytest -q`
Expected: all new catalog tests pass; only the pre-existing intermittent failures noted in CLAUDE.md (`test_seasonal_signals_are_included`, printify auth/content-policy) may fail — confirm no *new* failures.

- [ ] **Step 2: Add a CLAUDE.md note**

Append under the Design Pipeline Notes section:

```markdown
- **Printify catalog service** (`app/services/catalog/`): Redis-cached (24h TTL,
  background refresh, stale-serving + backoff) catalog with zero hardcoded IDs.
  Catalog API supplies blueprint/provider/variant/color-name/size; hex, per-variant
  cost, and per-color mockup URLs are harvested from created products via
  `catalog_service.ingest_product()` (bootstrapped from existing shop products,
  refreshed by the batch pipeline). `create_product` enables variants spread across
  up to `PRINTIFY_MAX_COLORS_PER_PRODUCT` colors so Printify renders a mockup per
  color (fixes always-black mockups). Per-product color stored on
  `Product.selected_color`; per-color URLs on `Product.color_mockups`. Endpoints
  under `/catalog`.
```

- [ ] **Step 3: Commit**

```bash
git add merchmind-backend/CLAUDE.md
git commit -m "docs(catalog): document the Printify catalog service"
```

---

## Self-review notes (addressed)

- **Spec coverage:** cache (T3), blueprint/provider/variant services (T4), variant_service color library + normalization + is_light (T2/T4/T5), mockup_service harvest + nearest fallback (T5), pricing_service (T6), catalog_service orchestrator + all getters (T6), `/catalog/colors` + `/catalog/mockup` + blueprints/sizes/refresh (T7), startup background warm + daily beat (T8), `selected_color`/`color_mockups` migration (T9), color-spread fix for always-black (T10), batch-pipeline harvest + default color (T11), dashboard client/types (T12), swatch component (T13), MockupTabs wiring with optimistic loading + persistence (T14), env tunables (T1), docs (T15).
- **Type consistency:** `harvest_from_product` returns the same color-library entry shape (`display_name, hex, is_light, variant_id, cost, front_url`) consumed by `catalog_service`, `pricing_service.price_range_from_library`, and `product_apply`. `get_colors` returns `{name, hex, is_light, has_mockup}` matching `CatalogColor` in the dashboard. `get_enabled_variant_ids` used identically in T6 and T10.
- **Known constraint:** dashboard `BLUEPRINT_PROVIDER` mirrors the backend maps for the 3 apparel types only — acceptable because color is apparel-only today and the backend remains the source of truth for resolution/publish.
