---
name: saas-redesign
description: Redesign the Vue 3 frontend into a modern SaaS-style interface with a left vertical navigation sidebar (replacing the top nav bar), a consistent spacing scale, and a polished professional look. Use when asked to modernize the UI, move navigation to a sidebar, restyle the app shell, or apply a cohesive SaaS visual layer.
---

# SaaS UI Redesign

Convert the app from a horizontal top-nav layout into a modern SaaS shell: a fixed
left **vertical sidebar** for navigation, a slim top bar for page context and global
controls, and content that follows a single, consistent spacing and design-token
system. The result should look like a professional product (Linear / Vercel / Stripe
dashboard family), not a restyled demo.

## Critical rules (do not skip)

- **Delegate every `.vue` create/modify to the `vue-expert` subagent** (project mandate
  in CLAUDE.md). This skill defines *what* to build and the exact tokens; vue-expert
  writes the Vue. Hand the agent the relevant section of this file verbatim.
- **Verify in the browser with Playwright MCP** (`mcp__playwright__*`) against
  `http://localhost:3000` after changes. Take screenshots at desktop (1440px) and a
  narrow width (≈900px). Don't claim "done" without a screenshot.
- **No emojis in the UI.** Use inline SVG icons (see Icons below).
- **Reuse the existing design tokens** — the global styles already live in
  `client/src/App.vue` (`<style>` block, not scoped). Extend that system; don't fork a
  second color palette.
- **Preserve behavior**: all existing routes, `FilterBar`, `ProfileMenu`,
  `LanguageSwitcher`, modals (`ProfileDetailsModal`, `TasksModal`), i18n via `t()`, and
  router-links must keep working. This is a visual/layout change, not a rewrite.

## Where things live (this repo)

- App shell + global styles: `client/src/App.vue`
- Routes (nav targets): `/` Overview, `/inventory`, `/orders`, `/spending` (Finance),
  `/demand` (Demand Forecast), `/reports`
- Nav labels are i18n keys: `t('nav.overview')`, `t('nav.inventory')`, `t('nav.orders')`,
  `t('nav.finance')`, `t('nav.demandForecast')`, plus `Reports`. Add any new strings to
  `client/src/locales/en.js` and `client/src/locales/ja.js`.
- Page chrome helpers already defined: `.page-header`, `.stat-card`, `.card`, `.badge`,
  `table`. Keep using them so pages stay consistent post-redesign.

## Design tokens

Add these as CSS variables on `:root` in `App.vue` and migrate hardcoded values to them.
The palette matches the existing slate/blue system — formalize it, don't replace it.

```css
:root {
  /* Surfaces */
  --bg-app: #f8fafc;          /* page background */
  --bg-surface: #ffffff;      /* cards, sidebar, top bar */
  --bg-sidebar: #0f172a;      /* dark sidebar (slate-900) */
  --bg-muted: #f1f5f9;        /* hover / subtle fills */

  /* Text */
  --text-strong: #0f172a;
  --text: #334155;
  --text-muted: #64748b;
  --text-on-dark: #cbd5e1;    /* sidebar idle label */
  --text-on-dark-strong: #ffffff;

  /* Brand / accent */
  --accent: #2563eb;
  --accent-soft: #eff6ff;
  --accent-on-dark: #3b82f6;

  /* Borders */
  --border: #e2e8f0;
  --border-strong: #cbd5e1;

  /* Status (already used by .badge / .stat-card) */
  --success: #059669; --warning: #ea580c; --danger: #dc2626; --info: #2563eb;

  /* Spacing scale — use ONLY these for layout gaps/padding */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem;
  --space-4: 1rem;    --space-5: 1.5rem; --space-6: 2rem; --space-8: 3rem;

  /* Radius */
  --radius-sm: 6px; --radius: 10px; --radius-lg: 14px;

  /* Elevation */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);

  /* Layout */
  --sidebar-w: 248px;
  --sidebar-w-collapsed: 72px;
  --topbar-h: 64px;
}
```

**Spacing discipline:** every layout gap, margin, and padding should be a `--space-*`
token. This is what produces the "consistent spacing" the user wants — inconsistent
ad-hoc rem values are the main thing that reads as unpolished.

## Layout architecture

Replace the column flex shell with a fixed-sidebar grid:

```
.app-shell  (display:grid; grid-template-columns: var(--sidebar-w) 1fr; min-height:100vh)
├── <Sidebar/>                  // fixed-width, full-height, dark
└── .app-main (display:flex; flex-direction:column; min-width:0)
    ├── .topbar (height var(--topbar-h)) — page title slot + LanguageSwitcher + ProfileMenu
    ├── <FilterBar/>            // kept; sits under the topbar
    └── main.content (padding: var(--space-5) var(--space-6); max-width:1600px)
        └── <router-view/>
```

Notes:
- `min-width:0` on `.app-main` prevents tables/charts from overflowing the grid track.
- Sidebar is `position: sticky; top:0; height:100vh` (or fixed) so it stays while content
  scrolls.
- Move `LanguageSwitcher` and `ProfileMenu` out of the old nav and into the topbar's
  right side. Move the logo/company name into the sidebar header.

## Sidebar component spec

Create `client/src/components/Sidebar.vue` (via vue-expert). Requirements:

1. **Header**: company name (`t('nav.companyName')`) + subtitle (`t('nav.subtitle')`),
   styled for the dark background. Acts as the brand block that used to be `.logo`.
2. **Nav list**: one `<router-link>` per route, each row = `icon + label`, vertical
   stack. Use `:class="{ active: $route.path === '/...' }"` exactly as the current
   top-nav does. Keep the i18n labels.
3. **Active state** on dark sidebar: filled accent-soft pill or left accent bar +
   brighter text. Idle = `--text-on-dark`, hover = subtle lighten + `--text-on-dark-strong`.
4. **Icons**: inline SVG, 20×20, `stroke="currentColor"`, `stroke-width="1.75"`, no fill.
   Suggested (lucide-style) per route: Overview→grid/layout-dashboard, Inventory→package,
   Orders→shopping-cart, Finance→dollar-sign/credit-card, Demand→trending-up,
   Reports→bar-chart. Define them inline; do not add a dependency.
5. **Collapse (optional, nice-to-have)**: a toggle that switches width to
   `--sidebar-w-collapsed` and hides labels (icons only) with `title` tooltips. Persist
   the boolean in a small composable or `localStorage`. Skip if scope is tight, but the
   layout var is already reserved for it.
6. **Footer (optional)**: app version / a muted line at the bottom.

Sidebar nav row reference styles:

```css
.nav-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin: 0 var(--space-2);
  border-radius: var(--radius-sm);
  color: var(--text-on-dark);
  font-size: 0.9rem; font-weight: 500;
  text-decoration: none;
  transition: background .15s ease, color .15s ease;
}
.nav-item:hover { background: rgba(255,255,255,0.06); color: var(--text-on-dark-strong); }
.nav-item.active { background: rgba(59,130,246,0.15); color: var(--text-on-dark-strong); }
.nav-item.active::before {  /* left accent bar */
  content:''; position:absolute; left:0; width:3px; height:1.5rem;
  background: var(--accent-on-dark); border-radius:0 3px 3px 0;
}
```

## Polish checklist (the "professional look")

- Consistent card system: every panel uses `.card` with `--radius` and `--border`; equal
  internal padding (`--space-5`); equal vertical rhythm (`--space-5` between sections).
- Topbar: thin bottom border (`--border`), `--bg-surface`, page title on the left
  (derive from route), controls right-aligned with `--space-3` gaps.
- Typography: page title 1.5–1.875rem/700, section title 1.125rem/700, body 0.875–0.938rem;
  `letter-spacing: -0.025em` on headings (already the convention).
- Hover/focus states on all interactive elements; visible `:focus-visible` outline for a11y.
- Empty/loading states use the existing `.loading` / `.error` classes.
- Responsive: below ~1024px the sidebar can collapse to icons or slide over with a
  hamburger in the topbar. At minimum it must not overlap content.

## Process

1. Read `client/src/App.vue` and the views to inventory current classes and routes.
2. Add design tokens to `:root` in `App.vue`; introduce the `.app-shell` grid + `.topbar`.
   (Delegate the `.vue` edit to vue-expert.)
3. Have vue-expert build `Sidebar.vue` and wire it into `App.vue`; relocate
   `ProfileMenu` + `LanguageSwitcher` into the topbar; remove the old `.top-nav`.
4. Sweep views (`client/src/views/*.vue`) only where spacing/cards diverge from the token
   system — keep changes minimal and consistent.
5. Add/verify i18n strings for any new labels in `en.js` and `ja.js`.
6. Start the app (`/start` skill or `npm run dev`) and verify with Playwright MCP:
   navigate each route, confirm active state, screenshot desktop + narrow widths.
7. Run the `code-reviewer` subagent on the changed `.vue` files.

## Done means

- Left vertical sidebar with icon+label nav, correct active state, brand header.
- Old top nav bar removed; global controls live in a slim topbar.
- All layout spacing comes from `--space-*` tokens; one shared palette.
- Every route renders, FilterBar + modals + i18n still work.
- Screenshots captured at 1440px and ~900px showing the new shell.
