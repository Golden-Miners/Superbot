# M11-UI-REVIEW.md

Retroactive 6-Pillar Visual Audit — Superbot Dashboard (M11 Dashboard/UX)
========================================================================

Audit type: Retroactive 6-pillar visual audit
Scope: All 8 dashboard surfaces (overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles)
Source files audited:
- src/superbot/m11/ui.py (surface renderers)
- src/superbot/m11/design_tokens.py (Swiss Style design tokens / CSS)
- src/superbot/m11/app.py (Streamlit entry point)
- src/superbot/m11/charts.py (Plotly OHLCV charts)
Phase: M11 (last completed UI phase)
Scoring scale: 1 (poor) → 4 (excellent)

---

## Pillar 1 — Layout / Grid / Spacing

**Score: 3 / 4**

### What works
- A complete 4px base-unit spacing system is defined as CSS custom properties
  (`--space-0` through `--space-12`, 0–48px).
- Spacing variables are consistently applied: metric cards use `var(--space-4)`
  padding, section headers use `var(--space-3)` margin-bottom, badges use
  `var(--space-1)`/`var(--space-3)` padding.
- Border radius tokens (`--radius-none`, `--radius-sm`, `--radius-md`,
  `--radius-lg`) are defined and used consistently.
- Layout is "wide" via Streamlit `layout="wide"`, giving the dashboard ample
  horizontal room for data-dense surfaces.

### What is missing / weak
- No explicit CSS grid or flex-column layout system beyond the utility classes;
  surfaces rely on Streamlit's default vertical flow.
- Data tables (jobs, audit events, settings profiles) are rendered as plain
  pipe-delimited text rather than actual HTML `<table>` elements because
  "HTML tables don't render reliably via st.markdown in this Streamlit
  version" (ui.py comment). This sacrifices alignment, borders, and
  scrollability that a real table would provide.
- No responsive breakpoints; single-column flow on all viewport sizes.

### Evidence
- `design_tokens.py` lines 67–77: spacing tokens.
- `design_tokens.py` lines 199–227: `.swiss-table` CSS (defined but unused in
  renderers — tables are plain text).
- `ui.py` lines 206–222, 310–318, 333–340: plain-text table rendering.

---

## Pillar 2 — Typography

**Score: 3 / 4**

### What works
- Complete font stack: `'Inter', -apple-system, BlinkMacSystemFont,
  'Segoe UI', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif`.
- Seven size tokens (`--font-size-xs` 0.75rem through `--font-size-4xl`
  2.25rem) with three line-height tokens (tight/normal/relaxed).
- Four font-weight tokens (400/500/600).
- Section headers use `font-size-lg` + `font-weight-semibold` with uppercase
  labels and letter-spacing for secondary text.
- Metric labels use `text-transform: uppercase` + `letter-spacing: 0.05em` for
  a Swiss-style microscopic label look.

### What is missing / weak
- No display-size heading beyond 4xl; page titles rely on Streamlit's
  `st.title`/`st.subheader` which bypass the CSS token system.
- Body text relies on Streamlit's `st.write`/`st.markdown` paragraph styles
  which partially override the CSS font settings.
- No typographic scale documentation showing when to use each size.

### Evidence
- `design_tokens.py` lines 49–65: typography tokens.
- `design_tokens.py` lines 267–290: `.stApp h1–h4`, `.stApp .stMarkdown p`
  overrides.
- `ui.py` lines 106–136: section headers + plain text body.

---

## Pillar 3 — Color

**Score: 4 / 4**

### What works
- Complete dual-mode palette (light + dark via `prefers-color-scheme`).
- Light mode: `#FFFFFF` background, `#000000` primary text, `#E0E0E0`
  borders. Dark mode: `#0A0A0A` background, `#FFFFFF` text, `#2A2A2A`
  borders.
- All surface, text, accent, border, divider, and focus-ring colors defined
  as CSS custom properties.
- Semantic badge variants: `--live` (accent bg, white text), `--blocked`
  (transparent, disabled border), `--neutral` (surface-elevated bg).
- Color is never the only signal: `health_badge()` and `gate_badge()` always
  pair text + icon alongside color.

### What is missing / weak
- No accent color beyond black/gray (by design — Swiss Style is neutral,
  but a single accent for CTAs or alerts would aid scannability).
- No semantic "success/warning/error" color variants beyond live/blocked.

### Evidence
- `design_tokens.py` lines 35–128: full light/dark color palette.
- `design_tokens.py` lines 149–165: badge variants.
- `design_tokens.py` lines 398–407: `health_badge()` text/icon redundancy.

---

## Pillar 4 — Components / Consistency

**Score: 2 / 4**

### What works
- A defined component vocabulary exists in CSS: `.swiss-badge`,
  `.swiss-metric-card`, `.swiss-section-header`, `.swiss-table`, `.swiss-btn`.
- All 8 surfaces apply `_badge()`, `_metric_card()`, `_section_header()`
  helpers consistently.
- Source labels are standardized via `source_label()` across all surfaces
  ("synthetic fixture — not live broker data", "broker feed — read-only,
  not live orders").
- CSS custom properties ensure every surface reads from the same token set.

### What is missing / weak
- **Critical typo:** `.swivl-btn:hover`, `.swivl-btn:focus-visible`,
  `.swivl-btn:disabled` (design_tokens.py lines 245–258) should be
  `.swiss-btn`. The button hover/focus/disabled states never apply because
  the class name is misspelled. The base `.swiss-btn` class is defined
  correctly but its interactive states are orphaned.
- `.swiss-btn` is defined in CSS but **never instantiated** in any UI
  renderer — no buttons exist on any surface.
- `.swiss-table` CSS is defined but **never used** — tables render as plain
  pipe-delimited text (see Pillar 1).
- No form inputs, dropdowns, or interactive components beyond Streamlit
  natives; the `.swiss-btn` component is orphaned.

### Evidence
- `design_tokens.py` lines 229–258: `.swiss-btn` defined, `.swivl-btn`
  typo for interactive states.
- `ui.py`: no `st.button` or `<button class="swiss-btn">` anywhere.
- `design_tokens.py` lines 199–227: `.swiss-table` unused; `ui.py` uses
  `u.write("...|...")` plain text instead.

---

## Pillar 5 — Motion / Interaction

**Score: 2 / 4**

### What works
- Transition tokens defined: `--transition-fast` (150ms ease),
  `--transition-normal` (200ms ease).
- Focus-visible ring (`--color-focus-ring`) defined for keyboard navigation.
- Button hover state intended (`background: var(--color-surface-elevated)`,
  `border-color: var(--color-text-secondary)`).

### What is missing / weak
- The `.swivl-btn` typo (Pillar 4) means hover/focus/disabled states never
  render — transitions are dead code.
- No animations, micro-interactions, or motion anywhere in the UI code.
- No loading states, empty states beyond "No jobs"/"No audit events"
  plain text, or error-state UI beyond "DATA UNAVAILABLE".
- No page transitions, fade-ins, or staggered reveals.

### Evidence
- `design_tokens.py` lines 95–96: transition tokens.
- `design_tokens.py` lines 245–258: broken button interactive states.
- `ui.py`: no animation classes, no loading spinners, no empty-state
  components beyond plain text.

---

## Pillar 6 — Accessibility / Usability

**Score: 3 / 4**

### What works
- Color is never the only signal: `health_badge()` returns text + icon
  (✓/⚠/✗) alongside color; `gate_badge()` returns text + icon-key.
- Focus-visible outline ring defined (`--color-focus-ring`).
- Minimum font size is `--font-size-xs` (0.75rem = 12px), above the
  12px accessibility floor.
- High-contrast palette: black-on-white light, white-on-black dark.
- All data explicitly labeled as "synthetic fixture" or "broker feed —
  read-only, not live broker data" — no fake success, no misleading
  live-data claims.
- Localhost-only binding (`127.0.0.1`), no public exposure.

### What is missing / weak
- No ARIA labels, roles, or live regions on any component.
- No skip-to-content link.
- No keyboard navigation enhancements beyond native Streamlit.
- The broken `.swivl-btn` typo also breaks `:focus-visible` for buttons
  (moot since no buttons exist, but still a defect).
- No reduced-motion (`prefers-reduced-motion`) handling despite
  transition tokens being defined.
- No font-size scaling for browser zoom (uses rem, which is good, but no
  explicit rem-based media queries).

### Evidence
- `design_tokens.py` lines 398–407: `health_badge()` text/icon redundancy.
- `design_tokens.py` lines 91–93, 119–120: shadow/focus-ring tokens.
- `ui.py` lines 126, 129, 133, 194, 232, 256, 308, 331: source labels on
  every surface.
- `app.py` line 47: `server.address 127.0.0.1`.

---

## Summary Scorecard

| Pillar | Score (1–4) | Grade |
|--------|-------------|-------|
| 1. Layout / Grid / Spacing | 3 | Good |
| 2. Typography | 3 | Good |
| 3. Color | 4 | Excellent |
| 4. Components / Consistency | 2 | Fair |
| 5. Motion / Interaction | 2 | Fair |
| 6. Accessibility / Usability | 3 | Good |
| **Overall average** | **2.83** | **Good** |

---

## Top Issues to Fix (in priority order)

1. **Fix `.swivl-btn` → `.swiss-btn` typo** (design_tokens.py lines 245–258).
   This single-character-class error breaks all button hover, focus, and
   disabled states. Since `.swiss-btn` is defined but never used, also
   consider whether buttons are needed on any surface.

2. **Replace plain-text tables with real HTML tables** (ui.py lines 206–222,
   310–318, 333–340). The `.swiss-table` CSS is already defined and unused;
   restore `_html()` rendering of `<table class="swiss-table">` for jobs,
   audit events, and settings profiles to regain alignment, borders, and
   scrollability.

3. **Add interactive components or remove orphaned CSS.** Either instantiate
   `.swiss-btn` buttons on surfaces that need actions (pause/resume/cancel
   jobs, toggle settings) or remove the unused button CSS to avoid
   dead-code confusion.

4. **Add loading/empty/error state components.** Currently "No jobs" and
   "DATA UNAVAILABLE" are plain `u.write()` strings with no visual
   hierarchy. Consider badged empty states or skeleton placeholders.

5. **Accessibility: add ARIA labels and `prefers-reduced-motion` handling.**
   The foundation (color + icon redundancy, focus ring) is solid; the ARIA
   and motion-reduction layers are missing.

---

## Conclusion

The M11 dashboard has a coherent Swiss Style design system with well-defined
tokens for spacing, typography, color, borders, and shadows. The color system
is particularly strong (dual-mode, color-never-alone principle). The main
defects are implementation gaps rather than design flaws: a CSS class-name
typo (`swivl-btn` vs `swiss-btn`), unused component CSS (`.swiss-table`,
`.swiss-btn`), and plain-text tables in place of real HTML tables. With the
top-5 fixes applied, the dashboard could move from a 2.83 to a 3.5+ overall.

---

*Audit conducted as part of M11 Dashboard/UX closure. All scores reflect the
implemented code as of this review; no rendering was performed in a live
browser — assessment is based on source-code inspection of UI, design tokens,
and entry-point files.*