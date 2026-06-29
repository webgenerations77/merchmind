# Printify Product Catalog Service + Mockup Color Fix — Design Spec

**Date:** 2026-06-29
**Author:** Drew + Claude
**Status:** Approved

## Problem

Two coupled problems:

1. **Hardcoded Printify IDs everywhere.** `printify_publisher.py` hardcodes
   `_BLUEPRINT_MAP`, `_PROVIDER_MAP`, `_SCALE_MAP`, `_FALLBACK_BASE_COSTS`. New
   colors/variants/blueprints never appear without a code change. There is no
   catalog abstraction and no catalog HTTP API.

2. **T-shirt mockups always render black.** Two root causes:
   - `create_product` enables only `all_variants[:20]` (`printify_publisher.py:181-184`).
     Printify renders mockups **only for enabled variants**, and the first 20 are
     frequently all one color (often black) in different sizes — so no other color
     mockup is ever generated.
   - `generate_mockups` grabs the **first** front image (`printify_publisher.py:329-339`)
     regardless of which color/variant it belongs to — defaulting to Printify's
     default (black) variant.

   There is no color selection anywhere in the data model, API, or dashboard. The
   `Product.variants` JSONB column exists but is never populated; there is no
   color column on `Product` or `Design`.

## Guiding Principle

**Zero hardcoded Printify IDs, color names, variant IDs, or blueprint IDs in new
code.** Colors, variants, blueprints, providers, costs, and mockups are discovered
and cached dynamically. `is_light` is computed from hex brightness, never from a
hardcoded list. (Existing hardcoded maps in `printify_publisher.py` remain as a
fallback safety net but are no longer the source of truth.)

## Key API constraint (verified 2026-06-29)

Printify's Catalog API exposes color **names only**, not hex. Per the variants
endpoint, `"options": { "color": "Heather Grey", "size": "XS" }` — no hex, no
per-variant cost. Therefore data sourcing is **split**:

- **Catalog API supplies:** blueprints, providers, variant IDs, color *names*, sizes.
- **Created products supply** the dynamic, design-coupled data:
  - `product.options[].values[].colors[]` → color **hex** → compute `is_light`.
  - `product.variants[].cost` → per-variant **cost**.
  - `product.images[]` (each with `variant_ids`, `position`, `is_default`, `src`)
    → your design's **per-color mockup URL**.

This fits the pipeline: products are created every batch, and the color library is
**bootstrapped** by ingesting existing shop products (`GET /shops/{shop}/products.json`)
on first refresh, then **kept fresh** by `catalog.ingest_product(product_json)` after
every `create_product`.

> Implementation note: exact field availability (e.g. whether catalog `variants.json`
> ever includes `cost`) is verified against a live API call during implementation.
> The fallback chain (product-sourced → catalog-sourced → `_FALLBACK_BASE_COSTS`)
> keeps pricing robust either way.

## Scope

In scope:
- New `app/services/catalog/` namespace (catalog service + sub-services).
- Redis-backed catalog cache with 24h freshness, background refresh, stale-serving,
  exponential backoff.
- Per-color mockup harvest from created products; fix the black-default selection.
- One Alembic migration: `Product.selected_color`, `Product.color_mockups`.
- New `/catalog` HTTP endpoints.
- Dashboard color-swatch picker (per product type) inside `MockupTabs.tsx`.
- Tunables documented in `.env.example`.

Out of scope (YAGNI):
- On-demand per-click mockup re-rendering (data is already harvested).
- Catalog-template (blank product) mockups.
- Per-size mockups.
- Any new Shopify API work; the two-store `target_store` logic is untouched.
- Removing the existing hardcoded maps (kept as fallback).

## Architecture & file layout

```
app/services/catalog/
  cache.py              # Redis JSON store: get/set with refreshed_at + TTL + backoff
  catalog_service.py    # orchestrator + public getters + ensure_fresh()/refresh()/ingest_product()
  blueprint_service.py  # blueprints from Catalog API
  provider_service.py   # providers per blueprint
  variant_service.py    # variants + color_library + name normalization + is_light
  mockup_service.py     # color→variant resolution, nearest-hex fallback, harvest per-color mockups
  pricing_service.py    # get_price(variant_id), get_price_range
app/routers/catalog.py  # GET /catalog/* endpoints
```

The existing `PrintifyService` (`app/services/publishing/printify_publisher.py`) stays
in place; its public interface is preserved. `create_product` and `generate_mockups`
are modified (see below) but keep their signatures.

## Cache layer (Redis)

Same JSON shapes the original spec named, stored under Redis keys instead of files:

- `catalog:blueprints` — list of blueprint metadata.
- `catalog:providers:{blueprint_id}` — providers for a blueprint.
- `catalog:variants:{blueprint_id}:{provider_id}` — variants (id, color name, size).
- `catalog:colors:{blueprint_id}:{provider_id}` — **color library**:
  `{normalized_color: {display_name, hex, is_light, variant_ids, sizes, mockup_url}}`.
- `catalog:manifest` — per-resource `refreshed_at` + last-refresh status/timing.

Behavior:
- Reads always serve from cache (target < 50ms; Redis reads are sub-ms).
- Freshness via stored `refreshed_at`; refresh when age > `PRINTIFY_CATALOG_TTL_HOURS`.
- Refresh runs in the background; never blocks a request or app startup.
- On refresh failure: keep serving stale, log the failure, retry with exponential
  backoff (1m → 5m → 15m → 1h) tracked in a Redis backoff key.
- Log every cache hit, miss, refresh attempt, and timing.

## Catalog service interface

```
get_blueprints()
get_blueprint(id)
get_providers(blueprint_id)
get_colors(blueprint_id, provider_id)              # [{name, hex, is_light, has_mockup}]
get_sizes(blueprint_id, provider_id)
get_variants(blueprint_id, provider_id)
get_variant(blueprint_id, provider_id, color, size) # → variant_id (+ cost)
get_mockups(blueprint_id, provider_id)
get_price(variant_id)                               # {cost, currency}
get_price_range(blueprint_id, provider_id)          # {min, max, currency}
search(query)
refresh()                                           # full rebuild from API + shop products
ensure_fresh()                                      # refresh only if stale (background-safe)
ingest_product(product_json)                        # harvest hex/cost/mockups from a created product
```

- Color names normalized for keys: lowercase + collapsed internal whitespace
  (`"Navy Blue"` == `"navy blue"`); display name preserved separately.
- `is_light = (R*299 + G*587 + B*114) / 1000 > 128`.
- `get_variant` resolves `(color, size)` → variant ID; nearest-hex fallback when the
  exact color is absent (Euclidean RGB distance).

## Mockup color flow (the fix)

1. **Enable a color spread at product creation.** `create_product` no longer slices
   `all_variants[:20]`. It uses the catalog to enable ≥1 variant across a spread of
   colors (all sizes per offered color), capped at `PRINTIFY_MAX_COLORS_PER_PRODUCT`
   to bound Printify render time. This makes Printify render one mockup per color.

2. **Harvest per-color mockups.** After creation, `catalog.ingest_product(product_json)`
   parses `product.images[]` + `product.options[]` + `product.variants[]` to build
   `{normalized_color: {display_name, hex, is_light, variant_id, front_url}}` and writes
   it to `Product.color_mockups`. Reuses the product JSON `generate_mockups` already
   fetches — no extra API calls.

3. **Fix default selection.** `generate_mockups` (and the dashboard) default to the
   product's `selected_color`, else the first catalog color for that blueprint — never
   "black" by name. The "grab first front image" logic is replaced by selecting the
   image whose `variant_ids` match the selected color's variant.

4. **Instant swatch switching.** The picker swaps between already-harvested URLs in
   `Product.color_mockups`; no per-click API call.

## Schema changes (one Alembic migration)

On `Product` (per the "color per product type" decision):

- `selected_color` — `String`, nullable. Normalized color name chosen for this product.
- `color_mockups` — `JSONB`, default `{}`:
  `{normalized_color: {display_name, hex, is_light, variant_id, front_url}}`.

The existing unused `Product.variants` JSONB holds enabled-variant/cost detail. No
`Design` schema change. Migration is additive and idempotent-safe; mirror into
`_apply_critical_schema_fallback()` in `main.py` per existing convention.

## New API endpoints (`/catalog`, behind `X-API-Key`)

- `GET /catalog/colors?blueprint_id=&provider_id=` → `[{name, hex, is_light, has_mockup}]`
- `GET /catalog/mockup?blueprint_id=&provider_id=&color=&camera=front`
  → `{mockup_url, color_name, hex, is_light}`. Generic helper: returns the most
  recently harvested mockup URL for that blueprint+provider+color from the
  `catalog:colors:*` library (nearest-hex fallback if the exact color is absent).
  **Not** tied to a specific design — the review queue itself swaps mockups using the
  already-loaded `Product.color_mockups` (no per-click call), so this endpoint is a
  convenience/debug surface, not on the hot path.
- `GET /catalog/blueprints` → cached blueprint list (picker support)
- `GET /catalog/sizes?blueprint_id=&provider_id=` → cached sizes
- `POST /catalog/refresh` → trigger a background refresh (admin/debug)

Register in `main.py` alongside existing routers.

## Dashboard changes

- New `ColorSwatchPicker` component: a row of circular swatches (hex fill; a light
  border when `is_light` so white/pale colors are visible; selection ring). Colors come
  from `GET /catalog/colors`; never defaults to black by name — default is the first
  catalog color for that blueprint.
- Placed **inside `MockupTabs.tsx`**, one swatch row per product tab (t-shirt / hoodie /
  long-sleeve), since color is per product type.
- On swatch click: show an optimistic loading state on the mockup image, swap to that
  color's harvested URL (from the product's `color_mockups`), and `PATCH /products/{id}`
  to persist `selected_color`.
- New `merchmind-dashboard/src/api/catalog.ts` module mirroring the existing axios
  client pattern (`client.ts`, `X-API-Key`, retry interceptor).
- `Product` type in the dashboard gains `selected_color` and `color_mockups`.

## Batch pipeline integration

In `_generate_design_for_trend` step 6b (`batch_pipeline.py:830-862`): after
`create_product` + `generate_mockups`, call `catalog.ingest_product(product_json)`, set
`product.color_mockups`, and set a default `product.selected_color` (first catalog color
for the blueprint). Reuses the already-fetched product JSON. Non-blocking: ingest
failures log and continue (mirrors the existing mockup fallback philosophy).

## Startup, refresh, backoff

- `catalog.ensure_fresh()` fired as a **background task** on FastAPI startup, added to
  the existing `@app.on_event("startup")` in `main.py` — non-blocking.
- Daily Celery Beat task `refresh_printify_catalog` for scheduled refresh.
- Stale-serving + exponential backoff (1m → 5m → 15m → 1h) per the cache layer.

## Env vars & docs

No new secrets (reuses `PRINTIFY_API_KEY`, `PRINTIFY_SHOP_ID`, `REDIS_URL`). New
tunables, documented in `merchmind-backend/.env.example`:

- `PRINTIFY_CATALOG_TTL_HOURS=24` — catalog cache freshness window.
- `PRINTIFY_MAX_COLORS_PER_PRODUCT=25` — caps enabled colors / Printify render load.

Both added to `app/config.py` `Settings`.

## Testing

Unit tests with mocked Printify responses (per the `unittest.mock` convention):

- Color name normalization (casing/whitespace).
- `is_light` brightness math at boundaries.
- Nearest-hex fallback selection.
- `get_variant` color+size → variant resolution.
- Cache hit / miss / stale / backoff transitions.
- `ingest_product` harvest parsing (options→hex, variants→cost, images→per-color URL).

## Explicitly preserved (unchanged)

- Approval → Printify publish → Shopify draft flow.
- Two-store `target_store` logic.
- Dynamic Mockups → Pillow fallback chain.
- `PrintifyService` public interface and existing fallback maps.

## Success criteria

- No new hardcoded Printify IDs, color names, variant IDs, or blueprint IDs.
- New colors/variants appear automatically after the next catalog refresh.
- No review-queue card shows a black mockup by default unless black is genuinely the
  first catalog color for that blueprint.
- Changing a swatch immediately updates the mockup preview.
- Selected color flows through to Printify publish and the Shopify listing.
- `is_light` computed from hex brightness, never a hardcoded list.
- Cached reads < 50ms; refresh runs in background without blocking startup or requests.
- New tunables documented in `.env.example`; approval→publish→draft flow unchanged.
