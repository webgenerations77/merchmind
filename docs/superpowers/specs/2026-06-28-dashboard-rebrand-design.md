# MerchMind Dashboard Re-theme — Design Spec

**Date:** 2026-06-28
**Scope:** `merchmind-dashboard/` only (web dashboard). Mobile app and Shopify theme are out of scope.
**Goal:** Replace the hardcoded dark theme with the official MerchMind brand system (`merchmind-dashboard/brand-kit/README.md`): a violet/mint identity with **light as the default surface** and a **dark theme available via toggle**.

## Decisions (locked)

1. **Theme mode:** Light default + dark toggle. Tokens architected as a `:root` (light) / `.dark` (dark) swap with a persisted user toggle.
2. **Scope:** Foundation pass — tokens, fonts, logo mark + wordmark, theme toggle, background textures, and a full recolor audit so every screen uses the new palette. Custom screen icons, empty-state illustrations, and feature-spot graphics are **Pass 2 (out of scope here)**.
3. **Token strategy:** Approach A — *remap-in-place + add brand primitives*. Keep existing semantic token names so components don't change; remap their values; add raw brand primitives; add a `.dark` override block.

## Current state (verified)

- **Tailwind v4**, CSS-based config via an `@theme` block in `src/index.css`. No `tailwind.config.js`.
- Current palette is hardcoded dark (`--color-bg-primary: #0A0A0A`, accent `#6366F1`, system fonts).
- Components reference **semantic token utility classes** (`bg-bg-primary`, `text-text-primary`, `text-accent`, `border-border`) consistently.
- **~26 hardcoded color usages** outside `index.css` to clean up: `ReviewPage.tsx` (17), `LoginScreen.tsx` (5), plus a few in `SuggestDrawer.tsx`, `CollectionsPage.tsx`, `DropsPage.tsx`, `ProductsPage.tsx`.
- **No icon library** (lucide/heroicons absent). Nav uses placeholder ASCII glyphs in `Sidebar.tsx`. Logo is a remote PNG fetched via `getLogoUrl('header')` with a text fallback.
- 10 pages; components grouped by feature under `src/components/`. Layout = `Layout.tsx` + `Sidebar.tsx`.

## Brand palette reference

Light/brand: `--paper #F6F5FB`, `--cream #EFEDF7`, `--violet-100 #ECE8FF`, `--violet-200 #D8CEFF`, `--violet-300 #B4A4FF`, `--violet #6D4AFF` (primary), `--violet-deep #5634E0`, `--mint-200 #B7F0E0`, `--mint #19D3A2` (signal), `--mint-deep #0FB488`, `--ink #15132B`, `--slate #3A3550`, `--muted #8B85A3`, `--alert #F2575B`.

Dark UI: `--d-bg #0F0E1A`, `--d-surface #1C1A2E`, `--d-border #2A2740`, `--d-text #E8E6F0`, `--d-muted #9A95B5`. Violet brightens to `#7C5CFF` on dark; mint stays `#19D3A2`. Mark on dark = violet-300 outline + mint core.

Principle: violet = workhorse (nav, primary actions, identity); mint = signal (live/success/data highlight); ink anchors text + dark base; `--alert` reserved for real errors only.

## Design

### 1. Token architecture — `src/index.css`

Three layers inside `@theme`:

**(a) Brand primitives** (new tokens, directly usable as `bg-violet`, `text-mint`, etc.):
`--color-paper, --color-cream, --color-violet-100, --color-violet-200, --color-violet-300, --color-violet, --color-violet-deep, --color-mint-200, --color-mint, --color-mint-deep, --color-ink, --color-slate, --color-muted, --color-alert`.

**(b) Semantic tokens** — existing names remapped to **light** values in `:root`:

| Token | Light value |
|---|---|
| `--color-bg-primary` | `--paper` `#F6F5FB` |
| `--color-bg-secondary` | `#FFFFFF` (cards) |
| `--color-bg-tertiary` | `--cream` `#EFEDF7` |
| `--color-bg-elevated` | `--violet-100` `#ECE8FF` |
| `--color-accent` | `--violet` `#6D4AFF` |
| `--color-border` | `#ECE9F5` |
| `--color-text-primary` | `--ink` `#15132B` |
| `--color-text-secondary` | `--slate` `#3A3550` |
| `--color-text-tertiary` | `--muted` `#8B85A3` |
| `--color-approve` | `--mint-deep` `#0FB488` |
| `--color-reject` | `--muted` `#8B85A3` |
| `--color-regen` | `--violet` `#6D4AFF` |
| `--color-delay` | `--violet-300` `#B4A4FF` |
| `--color-confidence-high` | `--mint-deep` `#0FB488` |
| `--color-confidence-medium` | `#EAB308` (keep amber) |
| `--color-confidence-low` | `--alert` `#F2575B` |

**(c) Dark overrides** — a `.dark { … }` block re-pointing the **same semantic CSS variables** to the dark palette: `bg-primary→--d-bg`, `bg-secondary→--d-surface`, `bg-tertiary→#211E3A`, `bg-elevated→--d-surface`, `border→--d-border`, `text-primary→--d-text`, `text-secondary→--d-muted`, `text-tertiary→--d-muted`, `accent→#7C5CFF`, `approve/confidence-high→--mint`.

Note on Tailwind v4: utility classes resolve `@theme` variables at build time, but the **runtime values** come from CSS custom properties, so overriding the same `--color-*` variables inside a `.dark` selector flips them live. The `.dark` block lives in `index.css` as a normal selector (not inside `@theme`).

Add radius/shadow tokens: card radius `8px`; light card shadow `0 1px 2px rgba(21,19,43,.08), 0 18px 44px rgba(21,19,43,.08)`.

### 2. Fonts

- Add Google Fonts `<link>` to `index.html`: `Space Grotesk:wght@400;500;600;700`, `Geist:wght@400;500;600`, `Geist Mono:wght@400;500`.
- Add font tokens to `@theme`: `--font-display` (Space Grotesk), `--font-sans` (Geist), `--font-mono` (Geist Mono).
- `body` font-family → Geist (replaces `system-ui`). Headings/wordmark → Space Grotesk with `letter-spacing:-0.02em`. SKUs/prices/eyebrow labels → Geist Mono (UPPERCASE labels, `letter-spacing:0.1–0.26em`).

### 3. Logo components — `src/components/brand/`

- `LogoMark.tsx` — faceted hexagon + mint core, built to kit geometry: `viewBox="0 0 120 120"`, outer hex path `M60 12 L101.6 36 L101.6 84 L60 108 L18.4 84 L18.4 36 Z` (stroke violet, width 4, round join), inner hex core `M60 40 L77.3 50 L77.3 70 L60 80 L42.7 70 L42.7 50 Z` (fill mint), 6 facet spokes (stroke violet, width 2, opacity .4). Props: `size`. Theme-aware via `currentColor`/tokens (light = violet outline; dark = violet-300). Drops spokes below ~30px; smallest size replaces inner hex with mint circle `r=14`.
- `Wordmark.tsx` — two-tone "**Merch**" (ink / d-text) + "**Mind**" (violet / violet-300), Space Grotesk 700, `-0.02em`.
- `Logo.tsx` — horizontal lockup (mark + wordmark, gap 24) for the sidebar; supports a stacked variant later.
- `Sidebar.tsx` swaps the `getLogoUrl('header')` PNG `<img>` for `<Logo />` in both the desktop rail header and the mobile top bar. Remote-logo plumbing (`getLogoUrl`, `logoConfig`) stays in the codebase but unused — no behavior break.

### 4. Theme toggle

- `useTheme` hook (`src/utils/` or `src/stores/`): state in `localStorage('mm-theme')`, default **light**; if unset, fall back to `prefers-color-scheme`. Toggling adds/removes `.dark` on `document.documentElement`.
- `ThemeToggle.tsx` — sun/moon button placed in the sidebar footer (next to Sign out) and in the mobile header bar.
- Inline blocking script in `index.html` `<head>` sets the initial `.dark` class from `localStorage` before React mounts, to avoid a flash of light theme.

### 5. Background textures

Add as utility classes in `index.css`, applied where the kit specifies (not plastered):
- `.bg-calm-wash` — `linear-gradient(165deg, var(--color-paper), var(--color-violet-100))` → default app shell (light).
- `.bg-dark-surface` — `radial-gradient(at 80% 0%, rgba(124,92,255,.28), transparent 50%), linear-gradient(160deg, var(--d-surface), var(--d-bg))` → app shell (dark).
- `.bg-brand-wash` — `linear-gradient(150deg, var(--color-violet), var(--color-violet-deep))` → opt-in for page headers / CTAs.
- `.bg-dot-grid`, `.bg-graph-paper` — available for studio/table surfaces; applied selectively.

### 6. Component recolor audit

- **Sidebar** — verify the light treatment: white/cream rail, violet active state (`bg-accent/15 text-accent` already maps to violet). Check contrast in both themes.
- **~26 hardcoded spots** — replace raw Tailwind colors (`bg-green-500`, literal `#hex`) with the matching semantic/primitive token. Priority: `ReviewPage.tsx` (17), `LoginScreen.tsx` (5), then `SuggestDrawer.tsx`, `CollectionsPage.tsx`, `DropsPage.tsx`, `ProductsPage.tsx`.
- **LoginScreen** — re-skin to the light brand: calm-wash (or violet-mesh) background, `<Logo />` lockup, violet primary button.
- Replace any remaining `bg-black/40` backdrops etc. with token-based equivalents where they'd clash in light mode.

### 7. Verification

Visual, so verify by running the dev server (`npm run dev`) and driving the browser via Claude-in-Chrome:
- Load every route in **light** and **dark**.
- Confirm no unreadable contrast, no leftover dark-on-dark / pure-black surfaces, mint/violet used per principle.
- Toggle persists across reload (localStorage) and no flash on load.
- Capture before/after screenshots of Dashboard, Review, and Login.

## Out of scope (Pass 2)

Custom screen icons (replace ASCII nav glyphs), empty-state illustrations, feature-spot graphics, app-icon export. The nav glyphs remain as-is for this pass.

## Risks / notes

- Tailwind v4 `@theme` + `.dark` runtime override: confirm the override approach works (it relies on CSS custom-property cascade, which Tailwind v4 supports). If a utility hardcodes a value at build time rather than referencing the variable, adjust by ensuring tokens are referenced as `var(--color-*)`.
- `confidence-medium` amber is kept (not in the brand palette) for traffic-light legibility; revisit if the kit later defines a warning tone.
- Don't delete the remote-logo plumbing — leave dormant to avoid breaking the Supabase logo upload flow.
