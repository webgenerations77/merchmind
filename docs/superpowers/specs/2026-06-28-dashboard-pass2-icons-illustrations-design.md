# MerchMind Dashboard Pass 2 — Icons & Illustrations Design Spec

**Date:** 2026-06-28
**Scope:** `merchmind-dashboard/` only. Builds on the Pass 1 re-theme (light-default brand tokens + dark toggle, already merged to `main`).
**Goal:** Replace the placeholder ASCII nav glyphs with a cohesive brand-styled icon set, consolidate duplicated inline utility icons, add the brand kit's 3 empty-state illustrations to the major empty pages, and give the login screen a brand hero. Brand reference: `merchmind-dashboard/brand-kit/README.md`.

## Decisions (locked)

1. **Icon source:** `lucide-react`, restyled to the brand aesthetic (line icons, `strokeWidth={2}`, color via `currentColor`, round caps). Lucide components are the shared icon abstraction — no custom `<Icon>` wrapper.
2. **Nav icons:** single-color (`currentColor`) so they inherit the existing active (violet `text-accent`) / inactive (`text-text-secondary`) states. No mint accent at nav size (reads as noise).
3. **Illustrations:** the 3 brand-kit empty-state illustrations are hand-authored SVG components (Lucide can't represent them). One shared `EmptyState` wrapper renders illustration + heading + optional subtext.
4. **Login hero:** violet-mesh background + a large low-opacity faceted-hexagon `LogoMark` motif. The kit's 5 feature-spot cards are OUT (marketing collateral, no home in the dashboard).

## Current state (verified by recon)

- No icon library installed; no shared Icon component. Three icon patterns today: ASCII nav glyphs (`<span className="text-base font-mono">{link.icon}</span>` in `Sidebar.tsx` lines 7-18, 92-94), the brand `LogoMark` component, and ad-hoc inline SVGs.
- Duplicated inline SVGs: hamburger/close-X (`Sidebar.tsx`), chevron down/up (`BatchDetailModal.tsx`, `ReviewPage.tsx` ×2), close-X + spinner (`SuggestDrawer.tsx`), sun/moon (`ThemeToggle.tsx`), star ×4 (`DashboardPage.tsx` ×2, `ReviewPage.tsx` ×2 — same path verbatim). Google "G" (`LoginScreen.tsx`) is brand-specific, leave it.
- ~19 empty states (mostly `py-16 text-center` or small inline panels). The big full-page ones: Review's 4 tabs (`ReviewPage.tsx` ~1580/1605/1620/1643), Collections (`CollectionsPage.tsx` ~150), Drops (`DropsPage.tsx` ~319), Drew's Mind (`DrewsMindPage.tsx` ~217), Marketing (`MarketingPage.tsx` ~134), Products filtered (`ProductsPage.tsx` ~474), API Usage full state (`ApiUsagePage.tsx` ~417). Small inline empties (Dashboard "No active alerts"/"No products yet", Settings clusters, modal sub-panels) stay text-only.
- Login screen (`LoginScreen.tsx`): `max-w-sm` card centered on `bg-app-shell`; surrounding space empty. No onboarding flow.

## Design

### 1. Nav icons (`Sidebar.tsx`)

Add `lucide-react` dependency. Replace the `icon: '#'` string field with a Lucide component reference. Render in the NavLink at 18px, `strokeWidth={2}`, inheriting `currentColor`.

Mapping:

| Nav item | Route | Lucide icon |
|---|---|---|
| Review | `/review` | `ClipboardCheck` |
| Dashboard | `/` | `LayoutDashboard` |
| Collections | `/collections` | `Layers` |
| Drew's Mind | `/drews-mind` | `Brain` |
| Drops | `/drops` | `Rocket` |
| Marketing | `/marketing` | `Megaphone` |
| Products | `/products` | `Tag` |
| Batches | `/batches` | `Boxes` |
| API Usage | `/api-usage` | `Activity` |
| Settings | `/settings` | `Settings` |

The `links` array changes from `{ to, label, icon: string }` to `{ to, label, Icon: LucideIcon }`. Render: `<link.Icon size={18} strokeWidth={2} />` in place of the mono span. Keep the `gap-3`, active/inactive classes, and the rest of the NavLink unchanged.

### 2. Utility-icon consolidation

Replace inline SVGs with Lucide named imports (matching size/className to current usage so layout is unchanged):
- `Sidebar.tsx` hamburger/close → `Menu` / `X` (driven by `open`).
- `BatchDetailModal.tsx`, `ReviewPage.tsx` (×2) chevron → `ChevronDown` with `className="transition-transform"` + a `rotate-180` toggle when expanded (preserve existing rotation behavior).
- `SuggestDrawer.tsx` close → `X`; spinner → `Loader2` with `animate-spin`.
- Star toggles (`DashboardPage.tsx` ×2, `ReviewPage.tsx` ×2) → `Star`, using `fill-current` when active/featured to preserve the filled-star look; keep existing sizes (`w-3`/`w-3.5`/`w-4`).
- `ThemeToggle.tsx` sun/moon → `Sun` / `Moon`.
- Leave `LogoMark`, `Wordmark`, and the Google "G" untouched.

No behavior change — purely swapping the SVG source. Each replacement preserves the element's existing classes (size, color, `animate-spin`, rotation), so theming and interactions are identical.

### 3. Empty-state illustrations

Create `src/components/empty/` with:
- `EmptyCanvas.tsx` — SVG: a canvas/frame rectangle, a faint t-shirt silhouette inside, a mint 4-point sparkle, a small violet cursor dot. ~160×160 default, `className` passthrough. Colors via brand tokens (`stroke-text-tertiary`/`stroke-violet`, `fill-mint`).
- `EmptyCatalog.tsx` — SVG: a price tag (rounded corner + hole), a mint eyelet dot, a small violet "+" badge.
- `EmptyData.tsx` — SVG: three bars on a baseline, a mint trend line rising to a mint node.
- `EmptyState.tsx` — wrapper: `{ illustration: ReactNode, heading: string, subtext?: string, action?: ReactNode }`, centered column (`flex flex-col items-center text-center gap-3 py-12`), heading in `font-display text-text-primary`, subtext in `text-text-tertiary text-sm`.

Illustrations are theme-aware via tokens (they use `stroke-*`/`fill-*` token utilities, so they adapt to dark mode automatically).

Placement — replace the existing centered-text empties on the big pages with `<EmptyState illustration={<…/>} heading=… subtext=… />`, preserving the current copy:

| Page / location | Illustration | Heading (existing copy kept) |
|---|---|---|
| Review — Batch tab | `EmptyCanvas` | "No batch designs to review" |
| Review — Collections tab | `EmptyCanvas` | "No collection designs to review" |
| Review — Drew's Mind tab | `EmptyCanvas` | "No Drew's Mind designs to review" |
| Review — Archived tab | `EmptyCanvas` | "No archived designs" |
| Drew's Mind page | `EmptyCanvas` | "No ideas yet" |
| Collections page | `EmptyCatalog` | "No collections yet" |
| Drops page | `EmptyCatalog` | "No drops yet" |
| Products (filtered empty) | `EmptyCatalog` | "No products found" |
| Marketing page | `EmptyData` | "No marketing assets yet" |
| API Usage (full empty state) | `EmptyData` | "No API usage recorded yet" |

Keep each page's existing subtext line. Small inline empties (Dashboard panels, Settings clusters, modal sub-panels) are NOT changed — illustrations would be oversized.

### 4. Login hero (`LoginScreen.tsx`)

- Change the page background from plain `bg-app-shell` to the kit's **violet-mesh** texture: add a `.bg-violet-mesh` utility to `index.css` per the brand kit (three radial gradients over `--color-paper`: violet `rgba(109,74,255,.24)` @18%/22%, mint `rgba(25,211,162,.22)` @84%/30%, violet-300 `rgba(180,164,255,.28)` @50%/94%, each `transparent ~56%`). Dark variant falls back to the existing dark-surface background.
- Add a large, low-opacity `LogoMark` motif (e.g. `size≈420`, `opacity-[0.06]`, absolutely positioned behind the card, pointer-events-none) so the empty space carries brand presence without competing with the sign-in card.
- The card, logo lockup, Google button, and copy from Pass 1 stay unchanged.

## Out of scope

- The brand kit's 5 feature-spot marketing cards (no dashboard surface hosts them).
- App-icon export, mobile app, Shopify theme.
- Redesigning small inline empty panels.

## Verification

No test runner (per Pass 1). Gate: `npx tsc -b` + `npm run build` pass; `npm run lint` introduces no new errors in touched files. Browser (Claude-in-Chrome) visual checks: the sidebar nav icons (light + dark, active + inactive states), at least one Review empty tab with its illustration, and the login hero. Authed-page empties that need sign-in are verified on the live deploy or via a local signed-in session.

## Risks / notes

- `lucide-react` is tree-shakeable (named imports only pull used icons) — bundle impact is small.
- Lucide `Star`/chevron must preserve existing `fill-current`/rotation behavior so the featured-star and accordion interactions look identical.
- Illustrations use token `stroke-*`/`fill-*` classes so they theme automatically; verify contrast in dark mode.
- The violet-mesh login background must remain readable behind the white card in light and the dark card in dark mode.
