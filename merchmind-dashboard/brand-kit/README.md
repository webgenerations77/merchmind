# Handoff: MerchMind — Brand & Graphics System

## Overview
**MerchMind** (merchmind-dashboard.vercel.app) is a merchandise design + management app. The brand is **clean, operational, and premium / studio-grade** — a precise tool that gets work done, with both **light and dark interfaces**. This package documents the full brand and graphics system: logo, app icon, color, typography, light/dark surfaces, background textures, core-screen iconography, empty-state illustrations, and feature spot graphics.

## About the Design Files
The file in this bundle (`MerchMind Brand Kit.dc.html`) is a **design reference created in HTML** — a prototype of the brand assets, not production code. It is a streaming "Design Component" that depends on a runtime (`support.js`); **do not ship it as-is.**

The task is to **recreate these assets in the target codebase's environment** (the live app is a React/Vercel dashboard) using its established patterns — export the logo/icons as real SVGs, the colors as design tokens/CSS variables (light + dark), the fonts via the app's font pipeline. Everything needed to rebuild without opening the HTML is documented below.

## Fidelity
**High-fidelity (hifi).** Final colors, type, geometry, and copy. All marks are simple geometric primitives (a hexagon + inner hexagon + straight facet lines) and reproduce exactly from the specs.

---

## Design Tokens

### Color — brand & light UI
| Token | Hex | Role |
|---|---|---|
| `--paper` | `#F6F5FB` | Light app background (cool violet-tinted) |
| `--cream` | `#EFEDF7` | Secondary light surface |
| `--violet-100` | `#ECE8FF` | Subtle fill / hover |
| `--violet-200` | `#D8CEFF` | Borders, tints |
| `--violet-300` | `#B4A4FF` | Muted accent / mark on dark |
| `--violet` | `#6D4AFF` | **Primary** — nav, primary action, identity |
| `--violet-deep` | `#5634E0` | Deep violet — gradients, pressed |
| `--mint-200` | `#B7F0E0` | Mint tint |
| `--mint` | `#19D3A2` | **Signal** — live/success/data highlight, logo core |
| `--mint-deep` | `#0FB488` | Deep mint |
| `--ink` | `#15132B` | Primary text + dark base |
| `--slate` | `#3A3550` | Secondary text |
| `--muted` | `#8B85A3` | Tertiary text / mono labels |
| `--alert` | `#F2575B` | Errors only |

### Color — dark UI
| Token | Hex | Role |
|---|---|---|
| `--d-bg` | `#0F0E1A` | Dark app background |
| `--d-surface` | `#1C1A2E` | Dark card/surface |
| `--d-border` | `#2A2740` | Dark borders |
| `--d-text` | `#E8E6F0` | Dark primary text |
| `--d-muted` | `#9A95B5` | Dark secondary text |

In dark UI: violet primary may brighten to `#7C5CFF`; mint stays `#19D3A2` (it pops on dark). Mark on dark uses `--violet-300` outline + `--mint` core.

Principle: violet is the workhorse (navigation, primary actions, identity); mint is the signal color (live status, success, "selling" moments, data highlights); ink anchors text and the dark theme; everything else is structural neutral.

### Typography
- **Display / wordmark — Space Grotesk**, weights 500/600/**700**. Precise, technical, premium. Wordmark + headlines. `letter-spacing: -0.02em`.
- **Text / UI — Geist**, weights 400/500/600. Clean neutral dashboard sans — tables, labels, controls.
- **Mono / labels — Geist Mono**, weights 400/500. SKUs, prices, deltas, eyebrow labels. UPPERCASE for labels, `letter-spacing: 0.1–0.26em`.

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap
```

### Radius & elevation
- App icon corner radius: **22.4%** (squircle).
- Card radius: `8px`. Swatches: `8px`. Inner UI: `7–10px`.
- Light card shadow: `0 1px 2px rgba(21,19,43,.08), 0 18px 44px rgba(21,19,43,.08)`.

---

## The Logo Mark (faceted hexagon + mint core)
Concept: a cut "gem" hexagon with a glowing mint core — premium, studio-grade, and reads as a "cell/mind". 

**Geometry** (SVG `viewBox="0 0 120 120"`, center 60,60, pointy-top regular hexagon, outer radius 48, `fill="none"`). Vertices:
`(60,12) (101.6,36) (101.6,84) (60,108) (18.4,84) (18.4,36)`.
- **Outer hexagon:** `path "M60 12 L101.6 36 L101.6 84 L60 108 L18.4 84 L18.4 36 Z"`, stroke `--violet`, width `4`, `stroke-linejoin:round`.
- **Inner hexagon (core):** radius 20, same orientation — vertices `(60,40)(77.3,50)(77.3,70)(60,80)(42.7,70)(42.7,50)` — `path "M60 40 L77.3 50 L77.3 70 L60 80 L42.7 70 L42.7 50 Z"`, **filled `--mint`**.
- **Facet spokes:** 6 thin lines (stroke `--violet`, width `2`, opacity `0.4`) joining each inner vertex to its matching outer vertex: `(60,12)-(60,40)`, `(101.6,36)-(77.3,50)`, `(101.6,84)-(77.3,70)`, `(60,108)-(60,80)`, `(18.4,84)-(42.7,70)`, `(18.4,36)-(42.7,50)`.

**Small sizes:** below ~30px, drop the spokes; at the smallest, replace the inner hexagon with a mint circle `r=14`.

**Reversed (on dark):** outer hexagon + spokes become `--violet-300`; core stays `--mint`.

### Wordmark & lockups
- Wordmark: **"MerchMind"** in **Space Grotesk 700**, `letter-spacing:-0.02em`, set as two tones: **"Merch" in `--ink`** + **"Mind" in `--violet`** (on dark: `--d-text` + `--violet-300`).
- **Primary lockup** (light): mark + wordmark, `gap:24px`; display scale mark ≈ 96px, wordmark ≈ 50px.
- **Reversed lockup** (dark): same on `--d-bg`.
- **Stacked:** mark above wordmark (`gap:16px`), wordmark ~34px, with mono tagline `DESIGN · SELL · TRACK` (`letter-spacing:0.26em`, `--muted`).
- Clearspace ≈ half the mark height around all sides.
- Tagline (Geist 500): **"Design it. Sell it. Track it."**

---

## App Icon Variants
22.4%-radius squircle, mark scaled to ~61%.
1. **Full color** — bg `linear-gradient(150deg, var(--violet), var(--violet-deep))`; hexagon + spokes white; core `--mint`. Shadow `0 14px 28px rgba(86,52,224,.34)`.
2. **Dark** — bg `linear-gradient(150deg,#211E3A,var(--ink))`; hexagon + spokes `--violet-300`; core `--mint`.
3. **Monochrome** — bg `--ink`; hexagon/spokes/core all white.
4. **Light tint** — bg `linear-gradient(150deg,#FFF,var(--violet-100))`, `1px` border `--violet-200`; full-color mark.

---

## Light & Dark UI Surfaces
The kit includes a paired surfaces panel demonstrating both themes:
- **Light:** `--paper` page, `#FFF` cards, `#ECE9F5` borders, violet primary button, ghost button `1px #DDD9EA`. Positive deltas in `--mint-deep` (`#0FB488`).
- **Dark:** `--d-bg` page, `--d-surface` cards, `--d-border` borders, violet primary button, ghost button `1px var(--d-border)`. Positive deltas in `--mint`.
Build both themes as token sets; components swap token values, not structure.

---

## Background Textures
1. **Dot grid** — `radial-gradient(rgba(109,74,255,.13) 1.4px, transparent 1.5px) 0 0 / 20px 20px, var(--paper)`. Use: studio canvas.
2. **Violet mesh** — three radials over `--paper`: violet `rgba(109,74,255,.24)` @18%/22%, mint `rgba(25,211,162,.22)` @84%/30%, violet-300 `rgba(180,164,255,.28)` @50%/94% (each `transparent ~56%`). Use: onboarding.
3. **Graph paper** — crossed `repeating-linear-gradient` at 0deg + 90deg, `rgba(21,19,43,.05)` lines every 24px, over `--cream`. Use: tables/ops.
4. **Calm wash** — `linear-gradient(165deg, var(--paper), var(--violet-100))`. Use: default screens.
5. **Brand wash** — `linear-gradient(150deg, var(--violet), var(--violet-deep))`. Use: headers/CTA.
6. **Dark surface** — `radial-gradient(at 80% 0%, rgba(124,92,255,.28), transparent 50%), linear-gradient(160deg,var(--d-surface),var(--d-bg))`. Use: dark mode.

---

## Iconography (core screens)
Line icons, `viewBox="0 0 48 48"`, stroke `--ink`, **stroke-width 2**, round caps/joins. Mint used as a single filled accent shape. Paths in the HTML; summary:
- **Dashboard** — 2×2 grid of rounded squares (`rx=3`); top-right cell filled `--mint`.
- **Design Studio** — a t-shirt outline + a small mint 4-point sparkle (merch + create).
- **Catalog** — a price tag (rounded corner + hole), mint dot for the eyelet.
- **Orders** — an isometric package/box (cube with top + center seam).
- **Analytics** — three bars on a baseline; the tall middle bar filled `--mint`.

---

## Empty-State Illustrations (geometric line art)
1. **Start designing** — a canvas/frame with a faint t-shirt on it + a mint sparkle and violet cursor dot. Headline: **"Your canvas is ready."** Background: dot grid.
2. **Empty catalog** — a price tag with a mint eyelet + a violet "+" badge. Headline: **"Add your first product."**
3. **No data yet** — three bar shapes with a mint trend line rising to a mint node. Headline: **"Insights start here."**

---

## Feature Spot Graphics
Five 236×300 cards, gradient bg, icon top-left, **Space Grotesk 700 25px** title + **Geist 13.5px** descriptor:
- **Dashboard** — `linear-gradient(155deg,#6D4AFF,#5634E0)`, white icon — "Everything, at a glance."
- **Design Studio** — `linear-gradient(155deg,#2A2748,#15132B)`, white icon — "Design merch that sells."
- **Catalog** — `linear-gradient(155deg,#19D3A2,#0FB488)`, dark-ink icon/text `#0A2F26` — "Your whole line, organized."
- **Orders** — `linear-gradient(155deg,#3A2F7A,#5634E0)`, white icon — "From cart to doorstep, tracked."
- **Analytics** — `linear-gradient(155deg,#211E3A,#0F0E1A)`, white icon (mint accent) — "Know what moves."

---

## Interactions & Behavior
Static reference. For the app: keep tone clean and operational. Violet = primary/identity; mint = success/live/data signal; reserve `--alert` for real errors. Support light and dark as a token swap.

## Assets to produce in-codebase
- Mark as SVG (full color, reversed/dark, monochrome) + small-size variants.
- App icon set at platform sizes (22.4% squircle).
- Core-screen icon set as SVGs.
- Empty-state illustrations as SVGs.
- Background textures as CSS gradients (above).
- Light + dark token sets.
- Fonts: Space Grotesk, Geist, Geist Mono.

## Files
- `MerchMind Brand Kit.dc.html` — full visual reference (open in a browser; all geometry/colors/copy documented above).
- `support.js` — runtime to render the reference only; not a deliverable.
