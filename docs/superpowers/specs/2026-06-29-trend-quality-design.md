# Trend Quality Fix — Design Spec

**Date:** 2026-06-29
**Scope:** `merchmind-backend/` only.
**Goal:** Stop batches from re-proposing concepts already designed/recently seen, and stop the approval-gate classifier from sending every trend to `image_with_text` (Ideogram). Together: fresher, varied, cost-efficient batches that actually exercise the (now-fixed) Flux path.

## Problem (verified)

1. **No cross-batch de-dup.** `batch_pipeline.py:181–191` de-dupes only *within a single scrape* (`seen = set()`, keyed on `raw_signal.lower().strip()`). It never checks existing designs or past batches, so recurring niche concepts ("Coffee Lovers: but first coffee", "Dog Lovers: dog mom") are re-proposed every run.
2. **No archetype variety in the approval flow.** Under mandatory trend approval, pre-classification (`:291–308`) calls `classify_archetype(trend.raw_signal, trend.source, niche_name)` **without a bias**, and the unbiased classifier strongly favors `image_with_text` → all trends route to Ideogram (~$0.08), and the cheap Flux path (~$0.003) is never used in batches. (Observed: a batch where all 4 proposed trends were `image_with_text`.) The 4-way bias rotation that guaranteed variety exists (`_BIAS_ROTATION` at `:344`) but only runs in the older inline/auto path.

## Decisions (locked)

1. **De-dup scope:** drop a trend if its normalized concept matches **any existing `Design.concept_name`** OR **any `Trend.raw_signal` from a batch in the last 8 weeks** (rolling window — concepts can resurface later). Covers both made designs and recently proposed-but-rejected trends.
2. **Variety:** apply the existing `_BIAS_ROTATION` (`image_only → text → image_text → image_with_text`) across queued trends during pre-classification, by index.
3. **Heavy-dedup behavior:** if de-dup leaves few/zero signals, proceed with what remains and log a clear warning (an empty approval gate signals the niches are tapped out). No silent failure, no fallback that re-introduces dupes.

## Design

### Unit 1 — `app/services/intelligence/trend_dedup.py` (new)

Kept as its own module so it imports **no celery** and is unit-testable locally (the rest of the suite avoids importing `batch_pipeline` for that reason).

- `normalize_concept(text: str) -> str` — lowercase, strip punctuation, collapse internal whitespace, strip. e.g. `"Coffee Lovers: But First Coffee!"` → `"coffee lovers but first coffee"`. Pure function.
- `build_seen_set(db, weeks: int = 8) -> set[str]` — returns a set of normalized concepts to exclude:
  - all `Design.concept_name` (where not deleted), normalized;
  - all `Trend.raw_signal` for trends whose batch `run_started_at` (or `created_at`) is within the last `weeks` weeks, normalized.
  - Two queries; normalize each into the set. Tolerant of `None`/empty values (skip them).
- `filter_unseen(signals: list[dict], seen: set[str]) -> list[dict]` — return signals whose `normalize_concept(signal["raw_signal"])` is **not** in `seen`. Pure (given `seen`).

### Unit 2 — `batch_pipeline.py` de-dup hook (`:181–191`)

Replace the within-scrape pre-filter so it seeds the `seen` set from the catalog/recent batches and uses the shared normalization:

```python
from app.services.intelligence.trend_dedup import normalize_concept, build_seen_set
...
seen = build_seen_set(db, weeks=8)          # cross-batch + existing designs
before = len(raw_signals)
filtered_signals = []
for signal in raw_signals:
    text = normalize_concept(signal["raw_signal"])
    if text in seen or len(text) < 3 or len(text.split()) > 12:
        continue
    seen.add(text)
    filtered_signals.append(signal)
raw_signals = filtered_signals
logger.info("Pre-filter (incl. cross-batch dedup): %d → %d signals", before, len(raw_signals))
```

This runs **before scoring**, so de-duped concepts never incur Claude scoring cost. Wrap `build_seen_set` in a try/except that, on error, logs and falls back to an empty set (degrade to old within-scrape-only behavior rather than crash the batch).

### Unit 3 — `batch_pipeline.py` archetype variety (`:291–308`)

In the pre-classification loop, give each queued trend a rotating bias and pass it to the classifier:

```python
for i, trend in enumerate(queued_trends):
    if not trend.proposed_archetype:
        try:
            niche_name = ...  # unchanged
            bias = _BIAS_ROTATION[i % len(_BIAS_ROTATION)]
            result = classify_archetype(trend.raw_signal, trend.source, niche_name, bias=bias)
            archetype = result["archetype"] if isinstance(result, dict) else result
            trend.proposed_archetype = archetype
            if not trend.selected_generator:
                api = select_image_api(archetype)
                trend.selected_generator = api or "text_only"
        except Exception:
            pass
db.commit()
```

`_BIAS_ROTATION` already exists in the module. `classify_archetype` already accepts `bias`. `select_image_api` maps archetype → generator (illustration/hybrid/text_icon → flux_schnell; image_with_text → ideogram; text_only/typographic → None→"text_only"). Net effect: a balanced spread including illustrations that route to Flux.

## Testing

- `tests/test_trend_dedup.py` (runs locally — no celery):
  - `normalize_concept`: punctuation/case/whitespace cases; e.g. two visibly-different strings of the same concept normalize equal.
  - `filter_unseen`: drops signals in `seen`, keeps novel ones, uses normalized comparison (a punctuation/case variant of a seen concept is dropped).
  - `build_seen_set`: with a mocked `db` whose queries return sample designs + recent trends, asserts the returned set contains the normalized concepts and skips `None`.
- Archetype variety: add an assertion (in a celery-guarded test, `pytest.importorskip("celery")`) that across N queued trends the assigned biases cycle through `_BIAS_ROTATION`. Reuses the already-tested `classify_archetype(bias=...)`.
- Verification gate: `pytest` green (the known-intermittent Printify integration test may fail — unrelated). Plus a real batch showing (a) no repeat of an already-designed concept, and (b) a varied archetype mix including at least one `illustration` (→ `flux_schnell`).

## Scope guard / out of scope

- Backend only: 1 new module, edits to `batch_pipeline.py` (two regions), new tests. No schema/migrations (uses existing `Design.concept_name`, `Trend.raw_signal`, batch timestamps). No frontend changes.
- Not changing the scrapers/niche clusters themselves, the scoring, or the niche-diversity selection (`:254–281`) — those stay.
- Not adding semantic/fuzzy matching (exact normalized match only) — YAGNI for now.

## Risks / notes

- Normalization must be identical on both sides (seen-set build and signal filtering) — both use `normalize_concept`. The existing pre-filter's weaker `.lower().strip()` is replaced by `normalize_concept` to unify.
- 8-week window uses batch timestamps; if a `Trend`→batch join is needed, query trends via their `batch_id` against batches started within the window (or use `Trend.created_at` if simpler and present). Implementer picks whichever column exists; behavior (last ~8 weeks of proposed trends) is the requirement.
- Heavy de-dup can yield a small/empty queue — that's acceptable and logged, not an error.
