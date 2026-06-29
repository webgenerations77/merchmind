# Product Title De-AI — Design Spec

**Date:** 2026-06-29
**Author:** Drew + Claude
**Status:** Approved

## Problem

Customer-facing store/Printify product titles read as AI-generated. Two causes:

1. The title base is `concept_name` — the raw scraped trend phrase, just title-cased
   (e.g. `"Sarcastic Office Coffee Mug Sayings"`). It's descriptive, not catchy.
2. The product type is joined with an **em-dash** (`"… — Tshirt"`), the single biggest
   AI tell Drew has called out (see `feedback_copy_voice`).

A better string already exists and is unused for this purpose: `shopify_title`, a
Claude-generated, brand-voiced, sanitized, max-60-char title stored on every design.

The 5 title-construction sites are also inconsistent: `batch_pipeline` and
`publish_queue` prefer `concept_name`; `idea_generator` and `collection_generator`
prefer `shopify_title`. All use em-dashes.

## Scope

In scope (per Drew, 2026-06-29):
- Customer-facing **store/product titles** only.
- Reuse the existing `shopify_title` (no new generator, no prompt hardening).
- **Backfill** existing live products in addition to fixing the pipeline.

Out of scope:
- The dashboard "Design Idea" label (`concept_name`) stays as-is.
- The `shopify_title` generation prompt is left unchanged.

## Design

### 1. Shared helper

Add to `app/services/design/shopify_copy_generator.py` (next to `sanitize_copy`):

```python
def build_product_title(product_type, *, shopify_title=None, concept_name=None):
    base = (shopify_title or concept_name or "Design").strip()
    label = product_type.replace("_", " ").title()
    return sanitize_copy(f"{base} - {label}")[:140]
```

- Prefers `shopify_title`, falls back to `concept_name`, then `"Design"`.
- `" - "` ASCII separator. `sanitize_copy` only strips em/en/double-dashes, so a
  single hyphen survives; em-dashes from upstream are still scrubbed.
- Caps at 140 chars (Printify title limit headroom).

### 2. Replace inline title constructions

Swap these to call `build_product_title(...)`:
- `app/tasks/batch_pipeline.py:842`
- `app/tasks/publish_queue.py:74` (also drops the concept_name-first `base_name` at :71)
- `app/tasks/idea_generator.py:232`
- `app/tasks/collection_generator.py:294`
- `app/tasks/drop_publisher.py:128`

Leave `publish_queue.py:104` (Shopify design-level draft title) — it already prefers
`shopify_title` and correctly has no product-type suffix.

### 3. Backfill endpoint

`POST /designs/backfill-product-titles`:
- Iterate `Product` rows with a non-null `printify_product_id`, excluding products
  whose design is deleted and products in `retired`/`unpublished` status.
- Recompute the title via `build_product_title` from the parent design's
  `shopify_title`/`concept_name`.
- `PUT /shops/{PRINTIFY_SHOP_ID}/products/{printify_product_id}.json` with
  `{"title": new_title}` via the publisher's existing `_request`.
- Swallow per-product failures with a logged warning; return `{scanned, updated, failed}`.
- Idempotent — safe to re-run.

### 4. Test

Unit test for `build_product_title`:
- Prefers `shopify_title` over `concept_name`.
- Output contains no em/en-dash.
- Includes the humanized product label.
- Falls back to `concept_name`, then `"Design"`.

## Risks

- Backfill issues a Printify `PUT` per product. Bounded by current product count
  (small — most verification test products were purged). Failures are non-fatal.
