# MerchMind Dashboard Pass 2 — Icons & Illustrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder ASCII nav glyphs with a brand-styled Lucide icon set, consolidate duplicated inline utility icons, add the brand kit's 3 empty-state illustrations to the major empty pages, and give the login screen a brand hero.

**Architecture:** Add `lucide-react` (tree-shakeable named imports) as the shared icon abstraction — no custom wrapper. Nav/utility icons inherit `currentColor` so they theme automatically. Empty-state illustrations are hand-authored SVG components styled with brand `stroke-*`/`fill-*` token utilities, rendered through one shared `EmptyState` wrapper. The login hero reuses the existing `LogoMark` plus a new violet-mesh background utility.

**Tech Stack:** React 19, TypeScript, Vite 8, Tailwind CSS v4, lucide-react.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-28-dashboard-pass2-icons-illustrations-design.md`. Brand reference: `merchmind-dashboard/brand-kit/README.md`.
- All work in `merchmind-dashboard/`. Do NOT touch `merchmind-backend/`, `merchmind-app/`, or `shopify-theme/`. Branch `dashboard-pass2` is already checked out.
- No test runner exists; do NOT add one. Verification gate: `npx tsc -b` and `npm run build` must PASS. The repo has ~22 pre-existing `eslint` errors — `npm run lint` is NOT a clean-pass gate; a task must only introduce **no new lint errors in the files it touches**. Browser visual checks are the controller's responsibility.
- Icons come from `lucide-react`, rendered as line icons (`strokeWidth={2}`), color via `currentColor`. Do NOT hardcode icon colors. Leave the brand `LogoMark`, `Wordmark`, and the Google "G" SVG (`LoginScreen.tsx`) untouched.
- Nav icon mapping (exact): Review→`ClipboardCheck`, Dashboard→`LayoutDashboard`, Collections→`Layers`, Drew's Mind→`Brain`, Drops→`Rocket`, Marketing→`Megaphone`, Products→`Tag`, Batches→`Boxes`, API Usage→`Activity`, Settings→`Settings`.
- Utility-icon swaps must preserve each element's existing classes (size, `animate-spin`, rotation, `fill-current`) so layout and interactions are unchanged. No behavior change.
- Illustrations use brand token utilities only (`stroke-text-tertiary`, `stroke-violet`, `fill-mint`, `fill-violet`, `stroke-mint`, `stroke-white`) so they theme in dark mode automatically.
- Empty-state copy: KEEP each page's existing heading and subtext text verbatim; only wrap it in `EmptyState` with an illustration. Do NOT change small inline empties (Dashboard panels, Settings clusters, modal sub-panels).
- Run commands from `merchmind-dashboard/`. Stage only the files each task changes (the repo has unrelated untracked files; never `git add -A`).

## File Structure

- `merchmind-dashboard/package.json` — MODIFY: add `lucide-react`.
- `src/components/layout/Sidebar.tsx` — MODIFY: nav icons + hamburger→`Menu`/`X`.
- `src/components/batches/BatchDetailModal.tsx`, `src/components/shared/SuggestDrawer.tsx`, `src/pages/DashboardPage.tsx`, `src/pages/ReviewPage.tsx`, `src/components/shared/ThemeToggle.tsx` — MODIFY: utility-icon swaps.
- `src/components/empty/EmptyCanvas.tsx`, `EmptyCatalog.tsx`, `EmptyData.tsx`, `EmptyState.tsx` — CREATE.
- Empty-state placement targets: `src/pages/ReviewPage.tsx`, `DrewsMindPage.tsx`, `CollectionsPage.tsx`, `DropsPage.tsx`, `ProductsPage.tsx`, `MarketingPage.tsx`, `ApiUsagePage.tsx` — MODIFY.
- `src/index.css` — MODIFY: add `.bg-violet-mesh`.
- `src/components/auth/LoginScreen.tsx` — MODIFY: hero background + `LogoMark` motif.

---

### Task 1: Add lucide-react and the Sidebar icons

**Files:**
- Modify: `merchmind-dashboard/package.json` (+ lockfile via install)
- Modify: `src/components/layout/Sidebar.tsx`

**Interfaces:**
- Produces: nav now renders Lucide icon components; the `links` array shape becomes `{ to: string, label: string, Icon: LucideIcon }`.

- [ ] **Step 1: Install lucide-react**

Run (from `merchmind-dashboard/`): `npm install lucide-react`
Expected: adds `lucide-react` to `dependencies`, no peer-dep errors (it supports React 19).

- [ ] **Step 2: Update the imports and `links` array in `Sidebar.tsx`**

Replace the existing import block and `links` array (top of file) with:

```tsx
import { NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  ClipboardCheck, LayoutDashboard, Layers, Brain, Rocket,
  Megaphone, Tag, Boxes, Activity, Settings, Menu, X,
  type LucideIcon,
} from 'lucide-react';
import { logout, type User } from '../../firebase';
import Logo from '../brand/Logo';
import ThemeToggle from '../shared/ThemeToggle';

const links: { to: string; label: string; Icon: LucideIcon }[] = [
  { to: '/review', label: 'Review', Icon: ClipboardCheck },
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/collections', label: 'Collections', Icon: Layers },
  { to: '/drews-mind', label: "Drew's Mind", Icon: Brain },
  { to: '/drops', label: 'Drops', Icon: Rocket },
  { to: '/marketing', label: 'Marketing', Icon: Megaphone },
  { to: '/products', label: 'Products', Icon: Tag },
  { to: '/batches', label: 'Batches', Icon: Boxes },
  { to: '/api-usage', label: 'API Usage', Icon: Activity },
  { to: '/settings', label: 'Settings', Icon: Settings },
];
```

- [ ] **Step 3: Render the nav icon instead of the mono glyph**

In the `links.map(...)` NavLink body, replace `<span className="text-base font-mono">{link.icon}</span>` with:

```tsx
              <link.Icon size={18} strokeWidth={2} />
```

Keep the surrounding `gap-3`, active/inactive classes, and `{link.label}` unchanged.

- [ ] **Step 4: Replace the mobile hamburger/close inline SVG with Lucide**

In the mobile header bar button, replace the inline `<svg>…</svg>` (the conditional 3-line / X) with:

```tsx
          {open ? <X size={22} strokeWidth={2} /> : <Menu size={22} strokeWidth={2} />}
```

Keep the button's existing classes and `aria-label`.

- [ ] **Step 5: Type-check, lint, build**

Run: `npx tsc -b && npm run build`
Expected: pass. Then `npm run lint` — confirm no NEW errors mention `Sidebar.tsx`.

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json src/components/layout/Sidebar.tsx
git commit -m "Add lucide-react; brand nav icons and Sidebar menu icon"
```

---

### Task 2: Consolidate utility icons in remaining files

**Files:**
- Modify: `src/components/batches/BatchDetailModal.tsx`, `src/components/shared/SuggestDrawer.tsx`, `src/pages/DashboardPage.tsx`, `src/pages/ReviewPage.tsx`, `src/components/shared/ThemeToggle.tsx`

**Interfaces:**
- Consumes: `lucide-react` (added in Task 1).

For each replacement, add the named import at the top of the file and swap the inline `<svg>…</svg>` for the Lucide component, preserving the existing wrapper classes (size, color, animation, rotation). Locate each by the description below.

- [ ] **Step 1: `ThemeToggle.tsx` — sun/moon → `Sun`/`Moon`**

Add `import { Sun, Moon } from 'lucide-react';`. Replace the two inline `<svg>` icons so the button renders:

```tsx
      {isDark ? <Sun size={18} strokeWidth={2} /> : <Moon size={18} strokeWidth={2} />}
```

Keep the button element, `aria-label`, and classes unchanged.

- [ ] **Step 2: `SuggestDrawer.tsx` — close-X → `X`, spinner → `Loader2`**

Add `import { X, Loader2 } from 'lucide-react';`. Replace the close-button inline X SVG with `<X size={20} strokeWidth={2} />` (keep the button's `w-5 h-5`/classes — set `size` to match). Replace the spinning loader inline SVG (the `animate-spin` circle+arc in the "Regenerating..." state) with `<Loader2 size={16} strokeWidth={2} className="animate-spin" />`.

- [ ] **Step 3: `BatchDetailModal.tsx` — chevron → `ChevronDown`**

Add `import { ChevronDown } from 'lucide-react';`. Replace the inline chevron `<svg>` (the `M19 9l-7 7-7-7` that rotates on expand) with:

```tsx
              <ChevronDown size={18} strokeWidth={2} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
```

Use the file's existing expanded-state variable name in place of `expanded` (read the surrounding code to confirm it). Keep the rotation behavior identical.

- [ ] **Step 4: `DashboardPage.tsx` — stars → `Star`**

Add `import { Star } from 'lucide-react';`. Replace the two inline star `<svg>` icons: the header badge star (`w-3.5 h-3.5 fill-white`) → `<Star size={14} className="fill-white text-white" />`; the per-card unfeature-toggle star (`w-3 h-3`) → `<Star size={12} className="fill-current" />`. Preserve each element's surrounding classes and click handlers.

- [ ] **Step 5: `ReviewPage.tsx` — chevrons → `ChevronDown`, stars → `Star`**

Add `import { ChevronDown, Star } from 'lucide-react';`. Replace:
- the reasoning-accordion chevron and the trend-row chevron (both inline, rotate on open) → `<ChevronDown size={16} strokeWidth={2} className={`transition-transform ${<existing open var>? 'rotate-180' : ''}`} />` (use the existing open-state variable at each site).
- the two star toggles (`w-4 h-4`) → `<Star size={16} className={<isFeatured> ? 'fill-current' : ''} />` (use the existing featured-state expression at each site; preserve the filled look when active).

Preserve all sizes, classes, and handlers.

- [ ] **Step 6: Type-check, lint, build**

Run: `npx tsc -b && npm run build`
Expected: pass. Then `npm run lint` — confirm no NEW errors in the five touched files (ReviewPage has known pre-existing errors; only NEW ones count).

- [ ] **Step 7: Commit**

```bash
git add src/components/batches/BatchDetailModal.tsx src/components/shared/SuggestDrawer.tsx src/pages/DashboardPage.tsx src/pages/ReviewPage.tsx src/components/shared/ThemeToggle.tsx
git commit -m "Replace duplicated inline utility icons with lucide-react"
```

---

### Task 3: Empty-state illustration components

**Files:**
- Create: `src/components/empty/EmptyCanvas.tsx`, `src/components/empty/EmptyCatalog.tsx`, `src/components/empty/EmptyData.tsx`, `src/components/empty/EmptyState.tsx`

**Interfaces:**
- Produces: `EmptyCanvas`, `EmptyCatalog`, `EmptyData` (default exports, props `{ className?: string }`), and `EmptyState` (default export, props `{ illustration: ReactNode; heading: string; subtext?: string; action?: ReactNode }`).

- [ ] **Step 1: Create `src/components/empty/EmptyCanvas.tsx`**

```tsx
export default function EmptyCanvas({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="Empty canvas">
      <rect x="34" y="30" width="92" height="100" rx="6" className="stroke-text-tertiary" strokeWidth="3" />
      <path
        d="M64 58 L72 52 L88 52 L96 58 L104 66 L96 74 L92 70 L92 104 L68 104 L68 70 L64 74 L56 66 Z"
        className="stroke-violet" strokeWidth="2.5" strokeLinejoin="round" opacity="0.5"
      />
      <path d="M112 40 L115 49 L124 52 L115 55 L112 64 L109 55 L100 52 L109 49 Z" className="fill-mint" />
      <circle cx="118" cy="118" r="5" className="fill-violet" />
    </svg>
  );
}
```

- [ ] **Step 2: Create `src/components/empty/EmptyCatalog.tsx`**

```tsx
export default function EmptyCatalog({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="Empty catalog">
      <path
        d="M54 54 L98 54 L120 76 C123 79 123 81 120 84 L84 120 C81 123 79 123 76 120 L54 98 Z"
        className="stroke-text-tertiary" strokeWidth="3" strokeLinejoin="round"
      />
      <circle cx="70" cy="70" r="6" className="fill-mint" />
      <circle cx="116" cy="116" r="14" className="fill-violet" />
      <path d="M116 110 V122 M110 116 H122" className="stroke-white" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
```

- [ ] **Step 3: Create `src/components/empty/EmptyData.tsx`**

```tsx
export default function EmptyData({ className = 'w-full h-full' }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 160" fill="none" className={className} role="img" aria-label="No data yet">
      <line x1="36" y1="118" x2="124" y2="118" className="stroke-text-tertiary" strokeWidth="3" strokeLinecap="round" />
      <rect x="48" y="92" width="16" height="26" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <rect x="72" y="74" width="16" height="44" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <rect x="96" y="84" width="16" height="34" rx="3" className="stroke-text-tertiary" strokeWidth="2.5" />
      <path d="M44 100 L72 80 L100 88 L120 54" className="stroke-mint" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="120" cy="54" r="6" className="fill-mint" />
    </svg>
  );
}
```

- [ ] **Step 4: Create `src/components/empty/EmptyState.tsx`**

```tsx
import type { ReactNode } from 'react';

interface EmptyStateProps {
  illustration: ReactNode;
  heading: string;
  subtext?: string;
  action?: ReactNode;
}

export default function EmptyState({ illustration, heading, subtext, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center gap-3 py-12">
      <div className="w-32 h-32">{illustration}</div>
      <h3 className="font-display font-semibold text-text-primary">{heading}</h3>
      {subtext && <p className="text-text-tertiary text-sm max-w-xs">{subtext}</p>}
      {action}
    </div>
  );
}
```

- [ ] **Step 5: Type-check, lint, build**

Run: `npx tsc -b && npm run build`
Expected: pass (components compile though not yet used). `npm run lint` — no new errors in the four files.

- [ ] **Step 6: Commit**

```bash
git add src/components/empty/
git commit -m "Add empty-state illustrations and EmptyState wrapper"
```

---

### Task 4: Wire EmptyState into the major empty pages

**Files:**
- Modify: `src/pages/ReviewPage.tsx`, `src/pages/DrewsMindPage.tsx`, `src/pages/CollectionsPage.tsx`, `src/pages/DropsPage.tsx`, `src/pages/ProductsPage.tsx`, `src/pages/MarketingPage.tsx`, `src/pages/ApiUsagePage.tsx`

**Interfaces:**
- Consumes: `EmptyState` and the three illustration components from Task 3.

**Method:** In each file, import what's needed (e.g. `import EmptyState from '../components/empty/EmptyState';` and the relevant illustration), then LOCATE the existing empty-state block by its heading text (listed below) and replace that centered-text block with an `<EmptyState illustration={<Illustration />} heading="…" subtext="…" />`, keeping the existing heading and subtext copy verbatim. Do not alter the surrounding conditional (`length === 0 ? ( … ) : ( … )`) — only swap the contents of the empty branch. Use this mapping:

| File | Locate by heading text | Illustration | Keep subtext (if present) |
|---|---|---|---|
| `ReviewPage.tsx` | "No batch designs to review" | `EmptyCanvas` | yes |
| `ReviewPage.tsx` | "No collection designs to review" | `EmptyCanvas` | yes |
| `ReviewPage.tsx` | "No Drew's Mind designs to review" | `EmptyCanvas` | yes |
| `ReviewPage.tsx` | "No archived designs" | `EmptyCanvas` | yes |
| `DrewsMindPage.tsx` | "No ideas yet" | `EmptyCanvas` | yes |
| `CollectionsPage.tsx` | "No collections yet" | `EmptyCatalog` | yes (the "Create one to get started." text) |
| `DropsPage.tsx` | "No drops yet" | `EmptyCatalog` | yes |
| `ProductsPage.tsx` | "No products found" | `EmptyCatalog` | (no subtext — omit) |
| `MarketingPage.tsx` | "No marketing assets yet" | `EmptyData` | yes |
| `ApiUsagePage.tsx` | "No API usage recorded yet" | `EmptyData` | yes (the "Usage tracking starts…" text) |

Note: a heading and its subtext may currently be split across two elements (e.g. `<p>` heading + `<p>` subtext). Move the heading string into `heading=` and the subtext string into `subtext=`; delete the now-redundant inline elements. Leave the `ApiUsagePage` smaller inline empties ("No calls found", "No API calls recorded yet") and all Dashboard/Settings inline empties unchanged.

- [ ] **Step 1: Apply the ReviewPage four tab empties**

Import `EmptyState` and `EmptyCanvas` in `ReviewPage.tsx`. Replace each of the four empty blocks (located by the heading text above) with the `EmptyState` form, preserving copy.

- [ ] **Step 2: Apply DrewsMindPage, CollectionsPage, DropsPage, ProductsPage, MarketingPage, ApiUsagePage**

In each file, import `EmptyState` + the mapped illustration and replace the located empty block per the table. (Products: omit `subtext`. Others: carry the existing subtext.)

- [ ] **Step 3: Type-check, lint, build**

Run: `npx tsc -b && npm run build`
Expected: pass. `npm run lint` — no new errors in the touched files.

- [ ] **Step 4: Commit**

```bash
git add src/pages/ReviewPage.tsx src/pages/DrewsMindPage.tsx src/pages/CollectionsPage.tsx src/pages/DropsPage.tsx src/pages/ProductsPage.tsx src/pages/MarketingPage.tsx src/pages/ApiUsagePage.tsx
git commit -m "Use illustrated EmptyState on major empty pages"
```

---

### Task 5: Login hero

**Files:**
- Modify: `src/index.css` (add `.bg-violet-mesh`)
- Modify: `src/components/auth/LoginScreen.tsx`

**Interfaces:**
- Consumes: `LogoMark` from `src/components/brand/LogoMark.tsx` and the new `.bg-violet-mesh` utility.

- [ ] **Step 1: Add the `.bg-violet-mesh` utility to `src/index.css`**

Add alongside the other texture utilities (after `.bg-graph-paper`):

```css
.bg-violet-mesh {
  background:
    radial-gradient(circle at 18% 22%, rgba(109, 74, 255, 0.24), transparent 56%),
    radial-gradient(circle at 84% 30%, rgba(25, 211, 162, 0.22), transparent 56%),
    radial-gradient(circle at 50% 94%, rgba(180, 164, 255, 0.28), transparent 56%),
    var(--color-paper);
}
.dark .bg-violet-mesh {
  background:
    radial-gradient(at 80% 0%, rgba(124, 92, 255, 0.28), transparent 50%),
    linear-gradient(160deg, #1C1A2E, #0F0E1A);
}
```

- [ ] **Step 2: Update `LoginScreen.tsx` — hero background + LogoMark motif**

Add `import LogoMark from '../brand/LogoMark';` (alongside the existing `Logo` import). Change the outer wrapper to use `bg-violet-mesh`, make it `relative overflow-hidden`, and add the decorative motif as the first child (behind the card):

```tsx
    <div className="min-h-screen bg-violet-mesh flex items-center justify-center p-4 relative overflow-hidden">
      <LogoMark size={420} className="absolute -left-24 -bottom-24 opacity-[0.06] pointer-events-none select-none" />
      <div className="relative ... (existing card classes unchanged) ...">
```

Keep the card (`bg-bg-secondary border …`), the `<Logo>` lockup, subtitle, Google button, error, and footer exactly as they are. The motif must sit BEHIND the card (card keeps/adds `relative` so it stacks above).

- [ ] **Step 3: Type-check, lint, build**

Run: `npx tsc -b && npm run build`
Expected: pass. `npm run lint` — no new errors in `LoginScreen.tsx`.

- [ ] **Step 4: Commit**

```bash
git add src/index.css src/components/auth/LoginScreen.tsx
git commit -m "Add violet-mesh login hero with LogoMark motif"
```

---

### Task 6: Visual verification (controller-driven)

**Files:** none.

- [ ] **Step 1: Build + serve**

Run: `npm run build && npm run preview` (or `npm run dev`).

- [ ] **Step 2: Verify the sidebar nav icons**

Via Claude-in-Chrome: confirm all 10 nav items show their Lucide icon (not ASCII), the active item's icon is violet, inactive icons are muted, and icons render in both light and dark. Hamburger/close works on mobile width.

- [ ] **Step 3: Verify an empty-state illustration**

Navigate to a reachable empty state (e.g. an empty Review tab or the login→authed flow if available). Confirm the illustration renders with mint/violet accents and themes correctly in dark mode. (Authed-only empties are verified on the live deploy.)

- [ ] **Step 4: Verify the login hero**

Sign out / load unauthenticated. Confirm the violet-mesh background, the faint LogoMark motif behind the card, and that the card + Google button remain clearly readable in light and dark.

- [ ] **Step 5: Final build check**

Run: `npx tsc -b && npm run build`
Expected: all pass. Branch ready for review/merge. Record any leftover visual issues and fix-forward per the same patterns.

---

## Self-Review

**Spec coverage:**
- §1 nav icons → Task 1 ✓ (dependency + mapping + render).
- §2 utility-icon consolidation → Task 1 (Sidebar hamburger) + Task 2 (other files) ✓.
- §3 empty-state illustrations → Task 3 (components) + Task 4 (placement, with the exact mapping table + kept copy) ✓.
- §4 login hero → Task 5 (`.bg-violet-mesh` + LogoMark motif) ✓.
- Out-of-scope (feature cards, small inline empties) correctly excluded ✓.
- Verification → Task 6 ✓.

**Placeholder scan:** Illustration SVGs, EmptyState, the icon mapping, and the login-hero CSS are all complete and concrete. Task 2/4 instruct locating sites by their existing variable/heading text (rather than guessing line numbers that shifted after Pass 1) — each carries the exact replacement form and the rule to preserve existing classes/copy, so there is no "figure it out" gap.

**Type consistency:** `EmptyState` prop shape `{ illustration, heading, subtext?, action? }` is consistent between Task 3 (definition) and Task 4 (usage — only `illustration`/`heading`/`subtext` used). Illustration component props `{ className? }` consistent. Lucide imports (`ClipboardCheck`, `LayoutDashboard`, `Layers`, `Brain`, `Rocket`, `Megaphone`, `Tag`, `Boxes`, `Activity`, `Settings`, `Menu`, `X`, `Sun`, `Moon`, `ChevronDown`, `Loader2`, `Star`) are all valid lucide-react named exports. `links` array shape change (`icon: string` → `Icon: LucideIcon`) is contained to Task 1 (Sidebar only).

**Risk note:** Tailwind v4 generates `fill-*`/`stroke-*` utilities from `--color-*` tokens, so `fill-mint`/`stroke-violet`/`stroke-text-tertiary` resolve; `stroke-white`/`fill-white` are built-ins. If an illustration color doesn't apply, confirm the token utility name matches a defined `--color-*`.
