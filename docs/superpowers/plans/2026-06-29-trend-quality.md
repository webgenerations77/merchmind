# Trend Quality Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De-dupe new batch trends against existing designs + recent proposals, and apply the bias rotation in approval-gate pre-classification so batches offer a varied archetype mix (incl. illustrations that route to the cheap Flux path).

**Architecture:** A new celery-free module `trend_dedup.py` holds the normalization + seen-set logic (unit-testable locally). `batch_pipeline.py` seeds its existing pre-filter from that seen-set (cross-batch de-dup before scoring) and assigns each queued trend a rotating bias from the existing `_BIAS_ROTATION` during pre-classification.

**Tech Stack:** Python 3.11, SQLAlchemy, pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-29-trend-quality-design.md`. Backend only (`merchmind-backend/`); no frontend, no schema/migrations. Branch `trend-quality-fix` is checked out.
- De-dup rule: drop a trend if `normalize_concept(raw_signal)` matches any existing `Design.concept_name` (not deleted) OR any `Trend.raw_signal` from the last **8 weeks** (`Trend.created_at >= now - 8 weeks`). Exact normalized match only — no fuzzy/semantic matching (YAGNI).
- `normalize_concept`: lowercase → strip punctuation (non-alphanumeric, non-space → space) → collapse whitespace → strip. `"Coffee Lovers: But First Coffee!"` → `"coffee lovers but first coffee"`.
- Variety: in pre-classification, each queued trend `i` gets `bias = _BIAS_ROTATION[i % len(_BIAS_ROTATION)]` passed to `classify_archetype(..., bias=bias)`. `_BIAS_ROTATION = ("image_only", "text", "image_text", "image_with_text")` currently exists ONLY as a **function-local** constant, defined twice (`batch_pipeline.py:344` and `:1012`). It must be **hoisted to module level** (single definition below the imports) so the pre-classification loop — which runs *before* those definitions — can use it; the two local re-definitions are then removed (the existing `archetype_bias = _BIAS_ROTATION[...]` lines at `:345`/`:1033` keep working against the module constant).
- Heavy-dedup behavior: proceed with whatever signals remain (even zero) and log it; never crash. `build_seen_set` failures degrade to an empty set (old within-scrape-only behavior), logged.
- Verification gate (this repo): `pytest` must pass EXCEPT the known-intermittent `tests/test_integrations.py::test_printify_health_check_ok` (documented flaky, unrelated). `batch_pipeline.py` can't be imported in the dev venv (no `celery`), so tests that import it must guard with `pytest.importorskip("celery")`; verify pipeline edits with `python -c "import ast; ast.parse(open(path).read())"` plus the full suite still collecting.
- Run commands from `merchmind-backend/`. The venv python is `.venv/Scripts/python.exe`. Stage only the files each task changes (the repo has unrelated untracked files; never `git add -A`).

## File Structure

- `app/services/intelligence/trend_dedup.py` — CREATE: `normalize_concept`, `build_seen_set`. No celery import.
- `tests/test_trend_dedup.py` — CREATE: unit tests (run locally).
- `app/tasks/batch_pipeline.py` — MODIFY: pre-filter hook (`:181–191`) for cross-batch de-dup; pre-classification loop (`:291–308`) for rotating bias.

---

### Task 1: `trend_dedup.py` + unit tests

**Files:**
- Create: `app/services/intelligence/trend_dedup.py`
- Create: `tests/test_trend_dedup.py`

**Interfaces:**
- Produces: `normalize_concept(text: str) -> str`; `build_seen_set(db, weeks: int = 8) -> set[str]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_trend_dedup.py`:

```python
from unittest.mock import MagicMock

import pytest

from app.services.intelligence.trend_dedup import normalize_concept, build_seen_set


@pytest.mark.parametrize("raw,expected", [
    ("Coffee Lovers: But First Coffee!", "coffee lovers but first coffee"),
    ("  Dog Lovers — Dog Mom  ", "dog lovers dog mom"),
    ("HELLO", "hello"),
    ("", ""),
    (None, ""),
])
def test_normalize_concept(raw, expected):
    assert normalize_concept(raw) == expected


def test_punctuation_and_case_variants_normalize_equal():
    assert normalize_concept("but first, COFFEE!") == normalize_concept("But First Coffee")


def test_build_seen_set_includes_designs_and_recent_trends():
    db = MagicMock()
    # build_seen_set makes two queries: designs first, then recent trends.
    db.query.return_value.filter.return_value.all.side_effect = [
        [("Coffee Lovers: But First Coffee!",)],   # Design.concept_name rows
        [("Dog Lovers — Dog Mom",)],               # Trend.raw_signal rows
    ]
    seen = build_seen_set(db, weeks=8)
    assert "coffee lovers but first coffee" in seen
    assert "dog lovers dog mom" in seen


def test_build_seen_set_skips_empty_values():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [
        [(None,)],   # design with null concept
        [("",)],     # trend with empty signal
    ]
    assert build_seen_set(db) == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_trend_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (module not created yet).

- [ ] **Step 3: Create the module**

Create `app/services/intelligence/trend_dedup.py`:

```python
"""Cross-batch trend de-duplication helpers.

Kept free of celery / batch_pipeline imports so it is unit-testable without
the Celery stack (the dev venv has no celery, so the rest of the suite avoids
importing batch_pipeline). batch_pipeline uses these to drop scraped concepts
already turned into designs or proposed in a recent batch.
"""
import re
from datetime import datetime, timedelta, timezone

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalize_concept(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    "Coffee Lovers: But First Coffee!" -> "coffee lovers but first coffee"
    """
    if not text:
        return ""
    no_punct = _PUNCT_RE.sub(" ", text.lower())
    return _WS_RE.sub(" ", no_punct).strip()


def build_seen_set(db, weeks: int = 8) -> set:
    """Normalized concepts to exclude from a new batch: every existing
    (non-deleted) design concept plus every trend raw_signal from the last
    `weeks` weeks."""
    from app.models.design import Design
    from app.models.trend import Trend

    seen: set = set()

    for (concept,) in db.query(Design.concept_name).filter(Design.is_deleted == False).all():  # noqa: E712
        norm = normalize_concept(concept)
        if norm:
            seen.add(norm)

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    for (raw,) in db.query(Trend.raw_signal).filter(Trend.created_at >= cutoff).all():
        norm = normalize_concept(raw)
        if norm:
            seen.add(norm)

    return seen
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_trend_dedup.py -v`
Expected: PASS (7 tests: 5 parametrized normalize + equal-variant + 2 build_seen_set).

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/trend_dedup.py tests/test_trend_dedup.py
git commit -m "Add trend_dedup: concept normalization + cross-batch seen-set"
```

---

### Task 2: Wire de-dup + archetype variety into `batch_pipeline.py`

**Files:**
- Modify: `app/tasks/batch_pipeline.py` (pre-filter `:181–191`; pre-classification `:291–308`)

**Interfaces:**
- Consumes: `normalize_concept`, `build_seen_set` from Task 1; `_BIAS_ROTATION` and `classify_archetype` (already in the module).

- [ ] **Step 1: Add the import and hoist `_BIAS_ROTATION` to module level**

Near the other intelligence imports (`batch_pipeline.py` already has `from app.services.intelligence import google_trends, reddit_scraper, twitter_scraper, seasonal_calendar`), add:

```python
from app.services.intelligence.trend_dedup import normalize_concept, build_seen_set
```

Then add this module-level constant just below the imports (above the first function), so both the pre-classification loop and the existing inline/approved generation paths share one definition:

```python
# Rotating archetype bias for balanced batches (image-only → text →
# image+text → image_with_text). Applied per queued trend by index.
_BIAS_ROTATION = ("image_only", "text", "image_text", "image_with_text")
```

And REMOVE the two now-redundant function-local re-definitions — delete this exact line at `batch_pipeline.py:344` and again at `:1012` (leave the `archetype_bias = _BIAS_ROTATION[...]` lines that follow each — they now reference the module constant):

```python
                _BIAS_ROTATION = ("image_only", "text", "image_text", "image_with_text")
```

- [ ] **Step 2: Replace the pre-filter block to seed cross-batch de-dup**

Replace the existing block (currently):

```python
        # Pre-filter: deduplicate and remove low-value signals before scoring
        seen = set()
        filtered_signals = []
        for signal in raw_signals:
            text = signal["raw_signal"].lower().strip()
            if text in seen or len(text) < 3 or len(text.split()) > 12:
                continue
            seen.add(text)
            filtered_signals.append(signal)
        logger.info(f"Pre-filter: {len(raw_signals)} → {len(filtered_signals)} signals")
        raw_signals = filtered_signals
```

with:

```python
        # Pre-filter: drop already-seen concepts (cross-batch de-dup against
        # existing designs + last-8-weeks trends) and low-value signals, all
        # before scoring so we don't spend Claude calls on concepts we discard.
        try:
            seen = build_seen_set(db, weeks=8)
        except Exception as e:
            logger.warning("build_seen_set failed (%s) — within-scrape dedup only", e)
            seen = set()
        before = len(raw_signals)
        filtered_signals = []
        for signal in raw_signals:
            text = normalize_concept(signal["raw_signal"])
            if text in seen or len(text) < 3 or len(text.split()) > 12:
                continue
            seen.add(text)
            filtered_signals.append(signal)
        raw_signals = filtered_signals
        logger.info(
            "Pre-filter (incl. cross-batch dedup): %d → %d signals", before, len(raw_signals)
        )
```

- [ ] **Step 3: Apply the rotating bias in pre-classification**

Replace the pre-classification loop (currently `for trend in queued_trends:` … using `classify_archetype(trend.raw_signal, trend.source, niche_name)`):

```python
        # Pre-classify archetype for each queued trend (for display in approval gate)
        for trend in queued_trends:
            if not trend.proposed_archetype:
                try:
                    niche_name = ""
                    if trend.niche_cluster_id:
                        cluster = db.query(NicheCluster).filter(NicheCluster.id == trend.niche_cluster_id).first()
                        if cluster:
                            niche_name = cluster.name
                    result = classify_archetype(trend.raw_signal, trend.source, niche_name)
                    archetype = result["archetype"] if isinstance(result, dict) else result
                    trend.proposed_archetype = archetype
                    if not trend.selected_generator:
                        api = select_image_api(archetype)
                        trend.selected_generator = api or "text_only"
                except Exception:
                    pass
        db.commit()
```

with (add `enumerate` + a rotating `bias` passed to the classifier):

```python
        # Pre-classify archetype for each queued trend (for display in approval
        # gate). Rotate the archetype bias so each batch offers a varied mix
        # (illustration→Flux, text, hybrid/text_icon, image_with_text→Ideogram)
        # instead of the unbiased classifier's heavy image_with_text skew.
        for i, trend in enumerate(queued_trends):
            if not trend.proposed_archetype:
                try:
                    niche_name = ""
                    if trend.niche_cluster_id:
                        cluster = db.query(NicheCluster).filter(NicheCluster.id == trend.niche_cluster_id).first()
                        if cluster:
                            niche_name = cluster.name
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

(`_BIAS_ROTATION` is now a module-level constant from Step 1, so it's in scope here.)

- [ ] **Step 4: Verify it parses and the suite still collects**

Run:
```bash
.venv/Scripts/python.exe -c "import ast; ast.parse(open('app/tasks/batch_pipeline.py').read()); print('batch_pipeline.py parses OK')"
.venv/Scripts/python.exe -m pytest -q
```
Expected: parse OK; suite collects and passes except the known-intermittent `test_printify_health_check_ok` (and `test_trend_dedup.py` passes). No NEW failures, no collection errors.

- [ ] **Step 5: Commit**

```bash
git add app/tasks/batch_pipeline.py
git commit -m "Wire cross-batch dedup and rotating archetype bias into batch pipeline"
```

---

### Task 3: Production verification (controller/user-driven)

**Files:** none.

- [ ] **Step 1: Deploy** (merge `trend-quality-fix` → `main`, push — Railway redeploy; do when no batch is generating).
- [ ] **Step 2: Run a batch** and inspect the approval gate via API: confirm (a) proposed trends are NOT concepts that already have designs, and (b) `proposed_archetype` shows a varied spread including at least one `illustration` (whose `selected_generator` is `flux_schnell`).
- [ ] **Step 3:** Approve an `illustration` trend, generate, and confirm the resulting design's `image_api_used == "flux_schnell"` — Flux exercised end-to-end in a real batch.

---

## Self-Review

**Spec coverage:**
- Unit 1 (`trend_dedup.py`: normalize_concept, build_seen_set) → Task 1 ✓ (filter_unseen dropped per YAGNI — the pipeline loop does the filtering inline using the two helpers).
- Unit 2 (de-dup hook at `:181`, before scoring, try/except degrade) → Task 2 Steps 1–2 ✓.
- Unit 3 (rotating bias in pre-classification) → Task 2 Step 3 ✓.
- Testing (dedup unit tests local; variety relies on existing classify tests) → Task 1 tests + Task 2 suite run ✓. (No separate bias-rotation unit test: it's a one-line `i % len` reusing the already-tested `classify_archetype(bias=...)`; testing it would require importing the celery-bound module. Verified by parse + production.)
- Heavy-dedup proceeds/logs; build_seen_set failure → empty set → Task 2 Step 2 ✓.
- Verification (no-repeat + varied + Flux-in-batch) → Task 3 ✓.

**Placeholder scan:** All code blocks complete. The one conditional instruction (hoist `_BIAS_ROTATION` if it's function-local) is a concrete, bounded action with a reporting requirement, not a vague placeholder.

**Type consistency:** `normalize_concept(str) -> str` and `build_seen_set(db, weeks=8) -> set` are consistent between Task 1 (definition) and Task 2 (use). The pipeline loop uses `normalize_concept` + the `seen` set from `build_seen_set` exactly as defined. `_BIAS_ROTATION`/`classify_archetype(bias=)`/`select_image_api` are pre-existing and used per their existing signatures.

**Resolved scope issue:** `_BIAS_ROTATION` was confirmed function-local (defined twice, at `:344` and `:1012`) and out of scope at the pre-classification loop. Task 2 Step 1 hoists it to a single module-level constant and removes both local re-definitions, so all three call sites share it. No remaining ambiguity.
