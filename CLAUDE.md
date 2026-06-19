# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MerchMind is an AI-powered print-on-demand merch pipeline. A weekly Celery batch scrapes trends (Reddit, Twitter, Google Trends), scores them with Claude/OpenAI, generates designs via DALL-E/Stable Diffusion, and queues products for Printify/Shopify publishing. A React Native mobile app lets the user review, approve/reject, and monitor everything.

## Repository Layout

- `merchmind-backend/` — FastAPI + Celery + PostgreSQL (Python 3.11)
- `merchmind-app/` — React Native 0.73 + Expo + TypeScript mobile app

## Backend Commands

All commands run from `merchmind-backend/`.

```bash
# Start infrastructure (Postgres + Redis)
docker compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed.py

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Celery worker
celery -A app.tasks.celery_app.celery_app worker --loglevel=info --concurrency=4

# Start Celery beat scheduler
celery -A app.tasks.celery_app.celery_app beat --loglevel=info

# Or start everything at once via Docker
docker compose up

# Run all tests
pytest

# Run a single test file
pytest tests/test_pricing.py

# Run a single test class or method
pytest tests/test_batch_pipeline.py::TestArchetypeClassifier::test_returns_valid_archetype
```

The venv Python is at `.venv/Scripts/python.exe` (Windows). Use it directly if `python` isn't on PATH.

## Mobile App Commands

All commands run from `merchmind-app/`. Package manager is npm.

```bash
npm install
npm start              # Metro bundler
npm run android        # Run on Android
npm run ios            # Run on iOS
npm test               # Jest
npm run lint           # ESLint
npm run type-check     # tsc --noEmit
```

The app defaults to mock mode (`USE_MOCK_API=true` in `.env`). Set it to `false` and configure `API_BASE_URL` to hit the real backend.

## Backend Architecture

**Request flow:** FastAPI routers → service classes → database (SQLAlchemy) or external APIs. Long-running work is dispatched to Celery tasks.

**Key patterns:**
- All endpoints require `X-API-Key` header (validated by `app/routers/auth.py`).
- Supabase Storage is used for all design/mockup file uploads via `app/utils/storage.py`. The `storage` singleton (`from app.utils.storage import storage`) exposes synchronous methods (`upload`, `upload_file`, `download`, `delete`, plus path helpers like `design_raw_path`, `mockup_path`). Callers throughout services and tasks use this singleton — do not change its interface.
- The Supabase client and Firebase are initialized lazily (on first call, not at import). Maintain this pattern to avoid startup crashes when credentials are missing.
- Config lives in `app/config.py` as a Pydantic `Settings` class reading from `.env`.

**Batch pipeline** (`app/tasks/batch_pipeline.py`): The core 10-step orchestrator that runs weekly (Sunday 10pm UTC via Celery Beat). It scrapes trends → scores them with LLMs → generates images → post-processes → creates products with pricing → emits progress via Redis pub/sub. The mobile app streams progress with SSE.

**Service namespaces under `app/services/`:**
- `intelligence/` — trend scraping and scoring (Reddit, Twitter, Google Trends, seasonal calendar)
- `design/` — archetype classification, prompt building, image generation, post-processing, quality scoring
- `pricing/` — dynamic pricing engine with floor prices, markup, and trend-based adjustment
- `marketing/` — social media asset generation (Instagram, TikTok, Pinterest, email, blog)
- `publishing/` — Printify product creation and Shopify listing
- `notifications/` — Expo push notifications and email

**Storage path conventions** (never change these):
```
designs/{design_id}/raw.png
designs/{design_id}/processed.png
designs/{design_id}/preview.png
designs/{design_id}/mockups/{product_type}/front.png
designs/{design_id}/mockups/{product_type}/back.png
designs/{design_id}/mockups/{product_type}/lifestyle.png
```

## Mobile App Architecture

- **Navigation:** React Navigation with conditional flow — MMKV checks onboarding completion, then either onboarding stack or main bottom-tab navigator (`src/navigation/`).
- **State:** Zustand typed stores in `src/store/` (batch, review, product, alert, settings).
- **API layer:** Axios client in `src/api/client.ts` with retry interceptor. Endpoint modules in `src/api/`. Mock data in `src/api/mock/data.ts`.
- **Path alias:** `@/*` maps to `src/*` (configured in `tsconfig.json` and `babel.config.js`).
- **Theme:** Design tokens in `src/theme/` (colors, typography, spacing).

## Deployment

Backend deploys to Railway (`railway.toml`) with three services: web (uvicorn), worker (Celery), beat (Celery Beat). The `Dockerfile` uses `python:3.11-slim` with system deps for Pillow, rembg, and psycopg2.

## Testing Notes

- Tests use `unittest.mock` to stub all external API calls.
- `tests/conftest.py` sets env var defaults (test DB on `merchmind_test`, Redis DB 1).
- Some integration tests (printify auth, image generator content policy) have known intermittent failures unrelated to storage or core logic.
