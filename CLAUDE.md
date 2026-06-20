# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MerchMind is an AI-powered print-on-demand merch pipeline. A weekly Celery batch scrapes trends (Reddit, Google Trends, seasonal calendar), scores them with Claude, generates designs via Flux Schnell (Replicate) with DALL-E fallback, creates Printify products with mockup previews, and queues everything for Shopify publishing. A web dashboard lets the user review, approve/reject, trigger batches, and monitor the pipeline.

## Repository Layout

- `merchmind-backend/` — FastAPI + Celery + PostgreSQL (Python 3.11)
- `merchmind-app/` — React Native 0.73 + Expo + TypeScript mobile app
- `merchmind-dashboard/` — React + Vite + TypeScript + Tailwind CSS web dashboard

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

**Note:** The mobile app uses `expo-constants` (not `react-native-config`) for env vars. Config is loaded via `app.config.js` which reads `.env` and exposes values through `Constants.expoConfig.extra`. EAS dev builds currently fail due to native module incompatibilities (`react-native-fast-image`, `react-native-haptic-feedback`, `react-native-mmkv`). These need swapping with Expo equivalents before EAS builds will work.

## Web Dashboard Commands

All commands run from `merchmind-dashboard/`.

```bash
npm install
npm run dev            # Vite dev server at localhost:5173
npm run build          # Production build to dist/
npm run preview        # Preview production build
```

`.env` requires `VITE_API_BASE_URL` and `VITE_API_KEY`. The dashboard connects directly to the Railway backend API.

## Backend Architecture

**Request flow:** FastAPI routers → service classes → database (SQLAlchemy) or external APIs. Long-running work is dispatched to Celery tasks.

**Key patterns:**
- All endpoints require `X-API-Key` header (validated by `app/routers/auth.py` using `APIKeyHeader` security scheme — Swagger UI shows an Authorize button).
- Swagger UI is enabled in production at `/docs`.
- Supabase Storage is used for all design/mockup file uploads via `app/utils/storage.py`. The `storage` singleton (`from app.utils.storage import storage`) exposes synchronous methods (`upload`, `upload_file`, `download`, `delete`, plus path helpers like `design_raw_path`, `mockup_path`). Callers throughout services and tasks use this singleton — do not change its interface.
- The Supabase client and Firebase are initialized lazily (on first call, not at import). Maintain this pattern to avoid startup crashes when credentials are missing.
- Config lives in `app/config.py` as a Pydantic `Settings` class reading from `.env`.

**Batch pipeline** (`app/tasks/batch_pipeline.py`): The core orchestrator that runs weekly (Sunday 10pm UTC via Celery Beat). Design generation runs **inline** (not as Celery subtasks) within the batch task. Steps: scrape trends → score with Claude → classify archetype → generate image (Flux Schnell/DALL-E) → upload to Supabase → create products with pricing → generate Printify mockups (tshirt, mug, phone_case) → generate marketing assets → emit progress via Redis pub/sub. Supports `max_designs` parameter for testing (`POST /batches/trigger?max_designs=2`).

**Service namespaces under `app/services/`:**
- `intelligence/` — trend scraping and scoring (Reddit, Twitter, Google Trends, seasonal calendar)
- `design/` — archetype classification, prompt building, image generation, post-processing, quality scoring, text preview generation
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

Backend deploys to Railway (`railway.toml`) with three services: web (uvicorn), worker (Celery), beat (Celery Beat). The `Dockerfile` uses `python:3.11-slim` with system deps for Pillow, rembg, psycopg2, and DejaVu fonts (for text preview rendering).

**Production URL:** `https://merchmind-production.up.railway.app`

**Important:** Pushing to `main` triggers a Railway redeploy which restarts the Celery worker, killing in-progress design generation tasks. Avoid pushing while batches are actively generating designs. Designs killed mid-generation get stuck at `status: "generating"` permanently.

**Phase 1 (current):** AI pipeline + Printify mockups working. Printify connected (shop ID 27979306, "Wear it Forward", Shopify sales channel). Printify creates draft products and generates mockup previews during batch runs. Shopify direct API access not yet configured (needs `shpat_` access token from Dev Dashboard custom app). Printify handles Shopify sync via its own integration.

**Phase 2 (future):** Direct Shopify API access for sales sync, order tracking, and product management. Deploy web dashboard to Vercel.

## Web Dashboard Architecture

- **Stack:** React 18 + TypeScript + Vite + Tailwind CSS
- **Routing:** React Router with 6 pages: Dashboard, Review, Drew's Mind, Products, Batches, Settings
- **State:** Zustand stores (mirrors mobile app pattern)
- **API:** Axios client with retry interceptor, same `X-API-Key` auth
- **Theme:** Dark theme matching mobile app design tokens from `merchmind-app/src/theme/colors.ts`

## Testing Notes

- Tests use `unittest.mock` to stub all external API calls.
- `tests/conftest.py` sets env var defaults (test DB on `merchmind_test`, Redis DB 1).
- Some integration tests (printify auth, image generator content policy) have known intermittent failures unrelated to storage or core logic.
- `test_seasonal_signals_are_included` has a known failure due to a mock pathing issue with the `intelligence` module.

## Design Pipeline Notes

- **Archetype classifier** (`app/services/design/archetype_classifier.py`): Balanced for a natural mix of visual and text designs. Falls back to `text_icon` (not `text_only`) on error. Archetypes: `illustration`, `hybrid`, `text_icon`, `typographic`, `text_only`.
- **Image generation** (`app/services/design/image_generator.py`): Primary: Flux Schnell (Replicate, ~$0.003/image). Fallback: gpt-image-1 (OpenAI, ~$0.03/image with `quality="low"`). All visual archetypes route to `flux_schnell` by default. Uses **sync** clients (not async) for Celery compatibility. DB enum `image_api` includes: `dalle3`, `stable_diffusion`, `flux_schnell`.
- **Text preview** (`app/services/design/text_preview.py`): Renders primary/secondary text with font pair label on a dark canvas using Pillow + DejaVu fonts. Uploaded to Supabase as the `processed_image_url`.
- **Post-processing:** rembg background removal is **skipped** (caused OOM on Railway worker). Raw generated images are used directly as processed images.
- **Printify mockups:** During batch generation, Printify draft products are created for tshirt, mug, and phone_case. Mockup images are fetched and stored in `product.mockup_urls`. Non-blocking — failures don't affect design completion.
- **COGS fallback:** When Printify API is unavailable for cost lookups, `get_base_cost()` returns industry-standard costs from `_FALLBACK_BASE_COSTS` (tshirt $8.50, mug $6.00, hat $10.00, phone_case $8.00, sticker $2.50, poster $12.00).
- **Product limit:** Max 4 product types per design (`assign_product_bundle` in `quality_scorer.py`).

## Weekly Schedule (Celery Beat)

- **Sunday 10pm UTC** — `run_weekly_batch`: scrape, score, generate designs + images + mockups
- **Monday 9am UTC** — `publish_approved_products`: push approved designs to Printify → Shopify
- **Monday 6am UTC** — `sync_shopify_sales`: fetch order data
- **Monday 7am UTC** — `check_underperformers`: flag low-performing products
- **Every 6 hours** — `health_monitor`: check service health

## Temporary Diagnostic Endpoints (remove before production)

- `POST /health/reset-data` — delete all pipeline data (keeps settings/clusters)
- `POST /health/purge-queue` — clear stuck Celery tasks
- `POST /health/test-image-gen` — test DALL-E + Flux Schnell image generation
- `POST /health/run-migration` — apply DB enum changes
- `GET /health/env-check` — show masked env var values
