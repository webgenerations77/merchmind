# MerchMind Dashboard Re-theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's hardcoded dark theme with the official MerchMind brand system — light-default violet/mint palette with a persisted dark toggle, brand fonts, an SVG logo, and background textures.

**Architecture:** Tailwind v4 CSS-first theming. Keep existing semantic token names (`--color-bg-primary`, `--color-accent`, …); remap their values to the light brand palette in `@theme`; override the same variables under a `.dark` selector for dark mode; add raw brand primitives and font/texture tokens. A Zustand store toggles the `.dark` class on `<html>` and persists to `localStorage`. Logo/wordmark become SVG React components.

**Tech Stack:** React 19, TypeScript, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Zustand, react-router-dom.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-28-dashboard-rebrand-design.md`. Brand reference: `merchmind-dashboard/brand-kit/README.md`.
- All work is in `merchmind-dashboard/`. Do NOT touch `merchmind-backend/`, `merchmind-app/`, or `shopify-theme/`.
- No test runner exists in this project; do NOT add one. Verification = `npx tsc -b` (type-check) + `npm run lint` + `npm run build`, plus browser-driven visual checks (Claude-in-Chrome) for themed surfaces.
- Default theme is **light**. Dark is opt-in via toggle, persisted at `localStorage` key `mm-theme` (`'light'` | `'dark'`).
- Brand palette (exact hex): paper `#F6F5FB`, cream `#EFEDF7`, violet-100 `#ECE8FF`, violet-200 `#D8CEFF`, violet-300 `#B4A4FF`, violet `#6D4AFF`, violet-deep `#5634E0`, mint-200 `#B7F0E0`, mint `#19D3A2`, mint-deep `#0FB488`, ink `#15132B`, slate `#3A3550`, muted `#8B85A3`, alert `#F2575B`. Dark: d-bg `#0F0E1A`, d-surface `#1C1A2E`, d-border `#2A2740`, d-text `#E8E6F0`, d-muted `#9A95B5`, violet-on-dark `#7C5CFF`.
- Principle: violet = nav/primary/identity; mint = signal (live/success/data); alert = real errors only.
- Keep the remote-logo plumbing (`assets/logos/logoConfig.ts`) in the repo but unused — do not delete it.
- Out of scope (Pass 2): custom screen icons, empty-state illustrations, feature-spot graphics, app-icon export. Leave the ASCII nav glyphs in `Sidebar.tsx` as-is.
- Run all commands from `merchmind-dashboard/`. The branch `dashboard-rebrand` already exists and is checked out.

## File Structure

- `src/index.css` — MODIFY: brand primitives, light semantic tokens, `.dark` overrides, font + radius tokens, texture utilities, body font.
- `index.html` — MODIFY: Google Fonts links + pre-mount theme init script.
- `src/stores/themeStore.ts` — CREATE: Zustand theme store (light/dark, persist, apply `.dark` class).
- `src/components/shared/ThemeToggle.tsx` — CREATE: sun/moon toggle button.
- `src/components/brand/LogoMark.tsx` — CREATE: faceted-hexagon SVG mark.
- `src/components/brand/Wordmark.tsx` — CREATE: two-tone "MerchMind" wordmark.
- `src/components/brand/Logo.tsx` — CREATE: mark + wordmark lockup.
- `src/components/layout/Sidebar.tsx` — MODIFY: use `<Logo />`, add `<ThemeToggle />`, drop remote-logo fetch.
- `src/components/layout/Layout.tsx` — MODIFY: app-shell background utility.
- `src/components/auth/LoginScreen.tsx` — MODIFY: re-skin to light brand + `<Logo />`.
- Recolor audit targets: `src/pages/ReviewPage.tsx`, `src/components/shared/SuggestDrawer.tsx`, `src/pages/CollectionsPage.tsx`, `src/pages/DropsPage.tsx`, `src/pages/ProductsPage.tsx`.

---

### Task 1: Token foundation, fonts, and textures

**Files:**
- Modify: `src/index.css` (full rewrite of the file)
- Modify: `index.html` (add font links + init script)

**Interfaces:**
- Produces: semantic utility classes unchanged in name (`bg-bg-primary`, `text-text-primary`, `text-accent`, `border-border`, `bg-approve`, `text-confidence-low`, …) but now light-valued, dark-aware. New primitive utilities: `bg-violet`, `text-violet`, `text-mint`, `fill-mint`, `stroke-violet`, `stroke-violet-300`, `text-ink`, `bg-paper`, etc. New font utilities: `font-display`, `font-sans`, `font-mono`. New texture utilities: `bg-app-shell`, `bg-brand-wash`, `bg-dot-grid`, `bg-graph-paper`. `dark:` variant enabled via `.dark` class on `<html>`.

- [ ] **Step 1: Rewrite `src/index.css`**

Replace the entire file with:

```css
@import 'tailwindcss';

/* Class-based dark mode: `.dark` on <html> */
@custom-variant dark (&:where(.dark, .dark *));

@theme {
  /* ---- Brand primitives ---- */
  --color-paper: #F6F5FB;
  --color-cream: #EFEDF7;
  --color-violet-100: #ECE8FF;
  --color-violet-200: #D8CEFF;
  --color-violet-300: #B4A4FF;
  --color-violet: #6D4AFF;
  --color-violet-deep: #5634E0;
  --color-mint-200: #B7F0E0;
  --color-mint: #19D3A2;
  --color-mint-deep: #0FB488;
  --color-ink: #15132B;
  --color-slate: #3A3550;
  --color-muted: #8B85A3;
  --color-alert: #F2575B;

  /* ---- Semantic tokens (LIGHT defaults) ---- */
  --color-bg-primary: #F6F5FB;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #EFEDF7;
  --color-bg-elevated: #ECE8FF;
  --color-accent: #6D4AFF;
  --color-border: #ECE9F5;
  --color-text-primary: #15132B;
  --color-text-secondary: #3A3550;
  --color-text-tertiary: #8B85A3;
  --color-approve: #0FB488;
  --color-reject: #8B85A3;
  --color-regen: #6D4AFF;
  --color-delay: #B4A4FF;
  --color-confidence-high: #0FB488;
  --color-confidence-medium: #EAB308;
  --color-confidence-low: #F2575B;

  /* ---- Fonts ---- */
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-sans: 'Geist', system-ui, sans-serif;
  --font-mono: 'Geist Mono', ui-monospace, monospace;

  /* ---- Radius ---- */
  --radius-card: 8px;
}

/* ---- Dark theme: override the same semantic variables ---- */
.dark {
  --color-bg-primary: #0F0E1A;
  --color-bg-secondary: #1C1A2E;
  --color-bg-tertiary: #211E3A;
  --color-bg-elevated: #1C1A2E;
  --color-accent: #7C5CFF;
  --color-border: #2A2740;
  --color-text-primary: #E8E6F0;
  --color-text-secondary: #9A95B5;
  --color-text-tertiary: #9A95B5;
  --color-approve: #19D3A2;
  --color-confidence-high: #19D3A2;
}

/* ---- Background textures ---- */
.bg-app-shell {
  background: linear-gradient(165deg, var(--color-paper), var(--color-violet-100));
}
.dark .bg-app-shell {
  background:
    radial-gradient(at 80% 0%, rgba(124, 92, 255, 0.28), transparent 50%),
    linear-gradient(160deg, #1C1A2E, #0F0E1A);
}
.bg-brand-wash {
  background: linear-gradient(150deg, var(--color-violet), var(--color-violet-deep));
}
.bg-dot-grid {
  background:
    radial-gradient(rgba(109, 74, 255, 0.13) 1.4px, transparent 1.5px) 0 0 / 20px 20px,
    var(--color-paper);
}
.bg-graph-paper {
  background:
    repeating-linear-gradient(0deg, rgba(21, 19, 43, 0.05) 0 1px, transparent 1px 24px),
    repeating-linear-gradient(90deg, rgba(21, 19, 43, 0.05) 0 1px, transparent 1px 24px),
    var(--color-cream);
}

@keyframes slide-in-right {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.animate-slide-in-right {
  animation: slide-in-right 0.2s ease-out;
}

body {
  margin: 0;
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 2: Add fonts + theme init to `index.html`**

In `<head>`, before the existing stylesheet/script tags, add the font links:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
```

Then, as the FIRST element inside `<head>` (so it runs before paint), add the theme init script:

```html
    <script>
      (function () {
        try {
          var t = localStorage.getItem('mm-theme');
          if (t === 'dark') document.documentElement.classList.add('dark');
        } catch (e) {}
      })();
    </script>
```

- [ ] **Step 3: Type-check, lint, build**

Run: `npx tsc -b && npm run lint && npm run build`
Expected: all succeed, no errors. (CSS-only + HTML changes; build must compile and Tailwind must emit the new utilities.)

- [ ] **Step 4: Browser smoke check**

Start dev server (`npm run dev`), open `http://localhost:5173` via Claude-in-Chrome. Expected: app renders on a light paper background; text is dark ink; no console errors about missing fonts. (Components are still partially dark-tuned — full polish comes in later tasks; here you only confirm the token swap took effect and nothing crashed.)

- [ ] **Step 5: Commit**

```bash
git add src/index.css index.html
git commit -m "Re-theme tokens: light-default brand palette, dark overrides, fonts, textures"
```

---

### Task 2: Theme store and toggle

**Files:**
- Create: `src/stores/themeStore.ts`
- Create: `src/components/shared/ThemeToggle.tsx`

**Interfaces:**
- Produces: `useThemeStore` (Zustand) exposing `{ theme: 'light' | 'dark', toggle(): void, setTheme(t): void }`. Default `ThemeToggle` component (named default export) rendering a button that calls `toggle()`.
- Consumes: nothing from other tasks. (Confirm `zustand` is a dependency: `grep zustand package.json` — it is, per existing stores.)

- [ ] **Step 1: Create `src/stores/themeStore.ts`**

```ts
import { create } from 'zustand';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'mm-theme';

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* ignore storage errors (private mode, etc.) */
  }
}

interface ThemeState {
  theme: Theme;
  toggle: () => void;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: getInitialTheme(),
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    set({ theme: next });
  },
  setTheme: (theme: Theme) => {
    applyTheme(theme);
    set({ theme });
  },
}));
```

- [ ] **Step 2: Create `src/components/shared/ThemeToggle.tsx`**

```tsx
import { useThemeStore } from '../../stores/themeStore';

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={`w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors ${className}`}
    >
      {isDark ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}
```

- [ ] **Step 3: Type-check + lint**

Run: `npx tsc -b && npm run lint`
Expected: passes. (Component is not yet mounted; this just verifies it compiles.)

- [ ] **Step 4: Commit**

```bash
git add src/stores/themeStore.ts src/components/shared/ThemeToggle.tsx
git commit -m "Add theme store and light/dark toggle button"
```

---

### Task 3: Brand logo components

**Files:**
- Create: `src/components/brand/LogoMark.tsx`
- Create: `src/components/brand/Wordmark.tsx`
- Create: `src/components/brand/Logo.tsx`

**Interfaces:**
- Produces: `LogoMark` (default export, props `{ size?: number; className?: string }`), `Wordmark` (default export, props `{ className?: string }`), `Logo` (default export, props `{ markSize?: number; wordmarkClassName?: string; className?: string }`).
- Consumes: the `stroke-violet`, `stroke-violet-300`, `fill-mint`, `text-violet`, `text-violet-300`, `text-text-primary`, `font-display` utilities from Task 1.

- [ ] **Step 1: Create `src/components/brand/LogoMark.tsx`**

Geometry is exact from `brand-kit/README.md` (viewBox 120×120, outer radius 48, inner core radius 20). Spokes drop below 30px; core becomes a circle below 20px.

```tsx
interface LogoMarkProps {
  size?: number;
  className?: string;
}

export default function LogoMark({ size = 40, className = '' }: LogoMarkProps) {
  const showSpokes = size >= 30;
  const useCircleCore = size < 20;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      className={className}
      role="img"
      aria-label="MerchMind"
    >
      <path
        d="M60 12 L101.6 36 L101.6 84 L60 108 L18.4 84 L18.4 36 Z"
        className="stroke-violet dark:stroke-violet-300"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      {showSpokes && (
        <g className="stroke-violet dark:stroke-violet-300" strokeWidth="2" opacity="0.4">
          <line x1="60" y1="12" x2="60" y2="40" />
          <line x1="101.6" y1="36" x2="77.3" y2="50" />
          <line x1="101.6" y1="84" x2="77.3" y2="70" />
          <line x1="60" y1="108" x2="60" y2="80" />
          <line x1="18.4" y1="84" x2="42.7" y2="70" />
          <line x1="18.4" y1="36" x2="42.7" y2="50" />
        </g>
      )}
      {useCircleCore ? (
        <circle cx="60" cy="60" r="14" className="fill-mint" />
      ) : (
        <path
          d="M60 40 L77.3 50 L77.3 70 L60 80 L42.7 70 L42.7 50 Z"
          className="fill-mint"
        />
      )}
    </svg>
  );
}
```

- [ ] **Step 2: Create `src/components/brand/Wordmark.tsx`**

Two-tone: "Merch" uses the primary-text token (ink → d-text auto-flips); "Mind" uses violet (→ violet-300 on dark).

```tsx
interface WordmarkProps {
  className?: string;
}

export default function Wordmark({ className = '' }: WordmarkProps) {
  return (
    <span className={`font-display font-bold tracking-[-0.02em] ${className}`}>
      <span className="text-text-primary">Merch</span>
      <span className="text-violet dark:text-violet-300">Mind</span>
    </span>
  );
}
```

- [ ] **Step 3: Create `src/components/brand/Logo.tsx`**

```tsx
import LogoMark from './LogoMark';
import Wordmark from './Wordmark';

interface LogoProps {
  markSize?: number;
  wordmarkClassName?: string;
  className?: string;
}

export default function Logo({
  markSize = 32,
  wordmarkClassName = 'text-xl',
  className = '',
}: LogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <LogoMark size={markSize} />
      <Wordmark className={wordmarkClassName} />
    </div>
  );
}
```

- [ ] **Step 4: Type-check + lint**

Run: `npx tsc -b && npm run lint`
Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add src/components/brand/
git commit -m "Add brand logo: faceted-hexagon mark, two-tone wordmark, lockup"
```

---

### Task 4: Wire logo + toggle into Sidebar and app shell

**Files:**
- Modify: `src/components/layout/Sidebar.tsx`
- Modify: `src/components/layout/Layout.tsx`

**Interfaces:**
- Consumes: `Logo` (Task 3), `ThemeToggle` (Task 2).
- Produces: nothing for later tasks.

- [ ] **Step 1: Update `src/components/layout/Sidebar.tsx`**

Replace the remote-logo logic with `<Logo />` and add `<ThemeToggle />`. Apply these edits:

1. Update imports at the top (remove `getLogoUrl`; add `Logo` and `ThemeToggle`):

```tsx
import { NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { logout, type User } from '../../firebase';
import Logo from '../brand/Logo';
import ThemeToggle from '../shared/ThemeToggle';
```

2. Remove the `headerLogo` state and its `useEffect`. The component keeps only the `open` state:

```tsx
export default function Sidebar({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
```

3. In the mobile header bar, replace the `headerLogo ? <img…> : <h1…>` block with the logo and add a toggle next to the avatar:

```tsx
        <Logo markSize={24} wordmarkClassName="text-base" />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <div className="w-9 h-9 flex items-center justify-center">
            {user.photoURL && (
              <img src={user.photoURL} alt="" className="w-7 h-7 rounded-full" />
            )}
          </div>
        </div>
```

4. In the desktop sidebar header (`<div className="p-5 border-b border-border">`), replace the `headerLogo ? <img…> : <h1…>` block:

```tsx
        <div className="p-5 border-b border-border">
          <Logo markSize={28} wordmarkClassName="text-lg" />
          <p className="text-xs text-text-tertiary mt-1.5">Spinach The Cow Merch Pipe</p>
        </div>
```

5. In the sidebar footer (`<div className="p-3 border-t border-border">`), add the toggle on the same row as Sign out. Replace the Sign out button block with:

```tsx
          <div className="flex items-center gap-2">
            <button
              onClick={logout}
              className="flex-1 px-3 py-1.5 rounded-lg text-xs text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-colors text-left"
            >
              Sign out
            </button>
            <ThemeToggle />
          </div>
```

- [ ] **Step 2: Update `src/components/layout/Layout.tsx`**

Give the app shell the brand background utility (light wash / dark surface):

```tsx
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import type { User } from '../../firebase';

export default function Layout({ user }: { user: User }) {
  return (
    <div className="flex min-h-screen bg-app-shell">
      <Sidebar user={user} />
      <main className="flex-1 p-4 md:p-6 overflow-auto pt-18 md:pt-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Type-check, lint, build**

Run: `npx tsc -b && npm run lint && npm run build`
Expected: passes with no unused-import errors (confirms `getLogoUrl` import was fully removed).

- [ ] **Step 4: Browser check (light + dark)**

`npm run dev`, open via Claude-in-Chrome. Verify: sidebar shows the hexagon mark + two-tone "MerchMind"; the app sits on the calm-wash background; clicking the toggle flips the whole app to dark and back; reload preserves the chosen theme (no flash). Capture a light and a dark screenshot of the Dashboard.

- [ ] **Step 5: Commit**

```bash
git add src/components/layout/Sidebar.tsx src/components/layout/Layout.tsx
git commit -m "Wire brand logo, theme toggle, and app-shell background into layout"
```

---

### Task 5: Re-skin the login screen

**Files:**
- Modify: `src/components/auth/LoginScreen.tsx`

**Interfaces:**
- Consumes: `Logo` (Task 3), `bg-app-shell` utility (Task 1).

- [ ] **Step 1: Update `src/components/auth/LoginScreen.tsx`**

Replace the heading block and outer background. Keep the Google button's `bg-white text-gray-800` (intentional Google branding). Apply:

1. Add the import:

```tsx
import { useState } from 'react';
import { signInWithGoogle } from '../../firebase';
import Logo from '../brand/Logo';
```

2. Change the outer wrapper to the brand shell:

```tsx
    <div className="min-h-screen bg-app-shell flex items-center justify-center p-4">
      <div className="bg-bg-secondary border border-border rounded-2xl p-8 w-full max-w-sm text-center shadow-[0_1px_2px_rgba(21,19,43,.08),0_18px_44px_rgba(21,19,43,.08)]">
        <div className="flex justify-center mb-2">
          <Logo markSize={40} wordmarkClassName="text-2xl" />
        </div>
        <p className="text-sm text-text-tertiary mb-8">Spinach The Cow Merch Pipe</p>
```

(Delete the old `<h1 className="text-2xl font-bold text-accent mb-1">MerchMind</h1>` line; the rest of the component — button, error, footer — stays unchanged.)

- [ ] **Step 2: Type-check, lint, build**

Run: `npx tsc -b && npm run lint && npm run build`
Expected: passes.

- [ ] **Step 3: Browser check**

Sign-out (or load the app unauthenticated) to view the login screen via Claude-in-Chrome in both themes. Verify the logo lockup renders, the card has a soft shadow on the light wash, and the Google button is still legible.

- [ ] **Step 4: Commit**

```bash
git add src/components/auth/LoginScreen.tsx
git commit -m "Re-skin login screen with brand logo and light wash"
```

---

### Task 6: Recolor audit of hardcoded colors

**Files:**
- Modify: `src/pages/ReviewPage.tsx`
- Modify: `src/components/shared/SuggestDrawer.tsx`
- Modify: `src/pages/CollectionsPage.tsx`
- Modify: `src/pages/DropsPage.tsx`
- Modify: `src/pages/ProductsPage.tsx`

**Interfaces:**
- Consumes: semantic + primitive token utilities from Task 1.
- Produces: nothing for later tasks.

**Mapping rules** (apply consistently — replace raw Tailwind/literal colors with tokens):

| Found | Replace with |
|---|---|
| `bg-green-*`, `text-green-*` (success/approve) | `bg-approve` / `text-approve` (or `bg-mint`/`text-mint` for a signal accent) |
| `bg-red-*`, `text-red-*` (error) | `bg-alert` / `text-alert` or `text-confidence-low` |
| `bg-blue-*`, `text-blue-*` (action/regen) | `bg-regen` / `text-regen` (violet) |
| `bg-purple-*`, `text-purple-*`, `bg-indigo-*` | `bg-accent` / `text-accent` (violet) |
| `bg-gray-*`, `text-gray-*`, `bg-zinc-*`, `bg-slate-*` (surfaces) | `bg-bg-tertiary` / `text-text-secondary` / `border-border` per role |
| `bg-yellow-*`, `text-yellow-*` (warning) | `text-confidence-medium` |
| literal `#hex` backgrounds/borders | nearest semantic token; if it's a brand color, the matching primitive |
| `bg-black/40` backdrop | keep (overlay scrim is theme-neutral) |
| Google button `bg-white text-gray-800` in LoginScreen | already handled in Task 5 — leave |

- [ ] **Step 1: Enumerate the remaining hardcoded colors**

Run: `npx grep` equivalent — search the five files for raw colors:

```bash
grep -nE "(bg|text|border|from|to|ring)-(gray|zinc|slate|neutral|indigo|blue|green|red|purple|emerald|yellow|amber)-[0-9]{2,3}|#[0-9A-Fa-f]{6}" src/pages/ReviewPage.tsx src/components/shared/SuggestDrawer.tsx src/pages/CollectionsPage.tsx src/pages/DropsPage.tsx src/pages/ProductsPage.tsx
```

Expected: a list of ~26 matches (heaviest in `ReviewPage.tsx`). Record each line.

- [ ] **Step 2: Apply the mapping per match**

For each match from Step 1, replace the raw color with the token from the mapping table above, preserving any opacity modifier (e.g. `bg-green-500/15` → `bg-approve/15`) and any `hover:`/`dark:` prefix. Do not change layout, spacing, or non-color classes. Leave overlay scrims (`bg-black/NN`) and the Google brand button as-is.

- [ ] **Step 3: Verify no raw colors remain**

Re-run the Step 1 grep. Expected: only intentional exceptions remain (overlay scrims, Google button colors already in LoginScreen which isn't in this list). If a match has no sensible token, default surfaces to `bg-bg-tertiary`/`text-text-secondary` and accents to `text-accent`.

- [ ] **Step 4: Type-check, lint, build**

Run: `npx tsc -b && npm run lint && npm run build`
Expected: passes.

- [ ] **Step 5: Browser check (Review page, light + dark)**

Open `/review` (the densest page) via Claude-in-Chrome in both themes. Verify badges/statuses read correctly, success = mint/mint-deep, errors = alert red, no leftover saturated green/blue/gray that clashes with the brand. Spot-check `/collections`, `/drops`, `/products`.

- [ ] **Step 6: Commit**

```bash
git add src/pages/ReviewPage.tsx src/components/shared/SuggestDrawer.tsx src/pages/CollectionsPage.tsx src/pages/DropsPage.tsx src/pages/ProductsPage.tsx
git commit -m "Recolor hardcoded page colors to brand tokens"
```

---

### Task 7: Full-app visual verification pass

**Files:** none (verification only).

- [ ] **Step 1: Build and serve**

Run: `npm run build && npm run preview`
Expected: production build succeeds; preview serves (default `http://localhost:4173`).

- [ ] **Step 2: Walk every route in light mode**

Via Claude-in-Chrome, with theme = light, load each route: `/review`, `/` (Dashboard), `/collections`, `/drews-mind`, `/drops`, `/marketing`, `/products`, `/batches`, `/api-usage`, `/settings`. For each, confirm: light paper/surface backgrounds, ink text, violet primary actions, mint signals, no pure-black panels, no dark-on-dark or unreadable contrast.

- [ ] **Step 3: Walk every route in dark mode**

Toggle to dark; repeat Step 2's walk. Confirm dark surfaces use `#0F0E1A`/`#1C1A2E` (not flat `#0A0A0A`), text is `#E8E6F0`, violet brightens, mint pops.

- [ ] **Step 4: Toggle persistence + no-flash**

Set dark, reload — app must come back dark with no light flash (init script). Set light, reload — comes back light. Confirm `localStorage['mm-theme']` matches.

- [ ] **Step 5: Record findings + fix-forward**

Note any screen with leftover hardcoded colors or contrast problems. For each, apply the Task 6 mapping rules to that file and commit a focused fix:

```bash
git add <file>
git commit -m "Fix <screen> theming: <what changed>"
```

- [ ] **Step 6: Final verification commit (if screenshots saved)**

If before/after screenshots were captured to a scratch location, no repo commit is needed for them. Confirm the branch builds clean one last time:

Run: `npx tsc -b && npm run lint && npm run build`
Expected: all pass. The `dashboard-rebrand` branch is ready for review/merge.

---

## Self-Review

**Spec coverage:**
- §1 token architecture → Task 1 ✓ (primitives, light semantics, `.dark` overrides).
- §2 fonts → Task 1 (links + tokens + body font) ✓.
- §3 logo components → Task 3; wired in Task 4 ✓.
- §4 theme toggle (store, persistence, no-flash script, placements) → Task 2 (store/toggle) + Task 1 (init script) + Task 4 (placements) ✓.
- §5 background textures → Task 1 (utilities) + Task 4 (app shell) + Task 5 (login) ✓.
- §6 component recolor (sidebar, ~26 spots, login) → Task 4 (sidebar), Task 5 (login), Task 6 (hardcoded spots) ✓.
- §7 verification → Task 7 ✓.
- Out-of-scope items (icons/illustrations) correctly excluded ✓.

**Placeholder scan:** No TBD/TODO; all code blocks are complete and concrete; mapping rules in Task 6 are explicit with a default-fallback rule so no match is left ambiguous.

**Type consistency:** `useThemeStore` shape `{ theme, toggle, setTheme }` is consistent between Task 2 (definition) and Task 4 (consumption via `ThemeToggle`). `Logo` props `{ markSize, wordmarkClassName, className }` consistent between Task 3 (definition) and Tasks 4/5 (usage: `markSize`, `wordmarkClassName`). `LogoMark` props `{ size, className }` consistent. Utility class names (`bg-app-shell`, `stroke-violet-300`, `fill-mint`, `text-violet`, `bg-approve`) defined in Task 1 and used in Tasks 3–6 match.

**Risk note carried from spec:** Tailwind v4 `.dark` override relies on CSS custom-property cascade; the `@custom-variant dark` declaration in Task 1 enables `dark:` utilities (used by `LogoMark`/`Wordmark`). If `dark:` variants don't apply, verify the `@custom-variant` line is present and `.dark` is on `<html>`.
