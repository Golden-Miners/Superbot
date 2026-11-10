"""M11 — Design tokens for Swiss Style / Minimalist theme.

Deterministic design token system for the Superbot local quant dashboard.
All values are defined as CSS custom properties so they can be injected
via st.markdown and used consistently across every surface.

Color palette — Swiss Style: neutral with black as the primary accent color.
- Light mode: near-white backgrounds, black text, gray borders
- Dark mode: near-black backgrounds, white text, dark gray borders

Typography:
- Font stack: Inter → system sans-serif → Helvetica Neue → Helvetica → Arial
- Sizes: xs (0.75rem) through 4xl (2.25rem)
- Line heights: tight (1.2), normal (1.5), relaxed (1.75)

Spacing:
- 4px base unit, scaled 4/8/16/24/32/48/64px

Borders:
- 1px solid #E0E0E0 (light) / #2A2A2A (dark)

Shadows:
- None or minimal (Swiss style avoids heavy shadows)

Read-only. Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

# CSS custom properties for Swiss Style / Minimalist theme.
# Injected into the Streamlit page via st.markdown(unsafe_allow_html=True).
CSS_VARIABLES = """
:root {
  /* ── Color palette — Swiss Style: neutral with black accent ── */
  --superbot-color-background: #FFFFFF;
  --color-surface: #FAFAFA;
  --color-surface-elevated: #F5F5F5;
  --color-text-primary: #000000;
  --color-text-secondary: #333333;
  --color-text-tertiary: #666666;
  --color-text-disabled: #999999;
  --color-accent: #000000;
  --color-accent-hover: #333333;
  --color-border: #E0E0E0;
  --color-divider: #F0F0F0;
  --color-focus-ring: rgba(0, 0, 0, 0.5);

  /* ── Typography ── */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-lg: 1.125rem;  /* 18px */
  --font-size-xl: 1.25rem;   /* 20px */
  --font-size-2xl: 1.5rem;   /* 24px */
  --font-size-3xl: 1.875rem; /* 30px */
  --font-size-4xl: 2.25rem;  /* 36px */

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;

  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* ── Spacing (4px base unit) ── */
  --space-0: 0;
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */

  /* ── Border radius ── */
  --radius-none: 0;
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 8px;

  /* ── Borders ── */
  --border-width: 1px;
  --border-style: solid;
  --border-color: #E0E0E0;

  /* ── Shadows (minimal — Swiss style avoids heavy shadows) ── */
  --shadow-none: none;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);

  /* ── Transitions ── */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;

  /* ── Streamlit component overrides ── */
  --st-primary-color: #000000;
  --st-secondary-background-color: #FAFAFA;
  --st-text-color: #000000;
  --st-secondary-text-color: #333333;
}

@media (prefers-color-scheme: dark) {
  :root {
    /* Color palette — dark mode */
    --color-background: #0A0A0A;
    --color-surface: #121212;
    --color-surface-elevated: #1A1A1A;
    --color-text-primary: #FFFFFF;
    --color-text-secondary: #B3B3B3;
    --color-text-tertiary: #666666;
    --color-text-disabled: #4A4A4A;
    --color-accent: #CCCCCC;
    --color-accent-hover: #E0E0E0;
    --color-border: #2A2A2A;
    --color-divider: #1A1A1A;
    --color-focus-ring: rgba(255, 255, 255, 0.5);
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);

    /* ── Streamlit dark overrides ── */
    --st-primary-color: #CCCCCC;
    --st-secondary-background-color: #121212;
    --st-text-color: #FFFFFF;
    --st-secondary-text-color: #B3B3B3;
  }
}

/* ── Utility classes ── */

.swiss-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  background: var(--color-surface);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.swiss-badge--live {
  background: var(--color-accent);
  color: var(--color-background);
  border-color: var(--color-accent);
}

.swiss-badge--blocked {
  background: transparent;
  border-color: var(--color-text-disabled);
  color: var(--color-text-disabled);
}

.swiss-badge--neutral {
  background: var(--color-surface-elevated);
  border-color: var(--color-border);
  color: var(--color-text-primary);
}

.swiss-metric-card {
  padding: var(--space-4);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.swiss-metric-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-text-primary);
}

.swiss-metric-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-tight);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: var(--space-1);
}

.swiss-section-header {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.swiss-table {
  width: 100%;
  border-collapse: collapse;
  border: var(--border-width) var(--border-style) var(--color-border);
}

.swiss-table th {
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: var(--space-2) var(--space-3);
  border-bottom: var(--border-width) var(--border-style) var(--color-border);
}

.swiss-table td {
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  padding: var(--space-2) var(--space-3);
  border-bottom: var(--border-width) var(--border-style) var(--color-divider);
}

.swiss-table tr:last-child td {
  border-bottom: none;
}

.swiss-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-normal);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  background: var(--color-surface);
  cursor: pointer;
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.swiss-btn:hover {
  background: var(--color-surface-elevated);
  border-color: var(--color-text-secondary);
}

.swiss-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-focus-ring);
}

.swiss-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Streamlit component overrides */
.stApp {
  background-color: var(--color-background);
  color: var(--color-text-primary);
  font-family: var(--font-family);
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family: var(--font-family);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.stApp h1 {
  font-size: var(--font-size-3xl);
  line-height: var(--line-height-tight);
  margin-bottom: var(--space-4);
}

.stApp h2, .stApp h3 {
  font-size: var(--font-size-xl);
  line-height: var(--line-height-tight);
  margin-top: var(--space-6);
  margin-bottom: var(--space-3);
}

.stApp .stMarkdown p, .stApp .stMarkdown li {
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-primary);
}

.stApp .stMetric {
  background: var(--color-surface);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.stApp .stMetric .stMetricValue {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.stApp .stMetric .stMetricLabel {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary);
}

.stApp .stButton button {
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  padding: var(--space-2) var(--space-4);
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.stApp .stButton button:hover {
  background: var(--color-surface-elevated);
  border-color: var(--color-text-secondary);
}

.stApp .stButton button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-focus-ring);
}
"""

# CSS variable names for reference in Python code
COLOR_BACKGROUND = "var(--color-background)"
COLOR_SURFACE = "var(--color-surface)"
COLOR_TEXT_PRIMARY = "var(--color-text-primary)"
COLOR_TEXT_SECONDARY = "var(--color-text-secondary)"
COLOR_TEXT_TERTIARY = "var(--color-text-tertiary)"
COLOR_ACCENT = "var(--color-accent)"
COLOR_BORDER = "var(--color-border)"
COLOR_DIVIDER = "var(--color-divider)"

FONT_FAMILY = "var(--font-family)"
FONT_SIZE_XS = "var(--font-size-xs)"
FONT_SIZE_SM = "var(--font-size-sm)"
FONT_SIZE_BASE = "var(--font-size-base)"
FONT_SIZE_LG = "var(--font-size-lg)"
FONT_SIZE_XL = "var(--font-size-xl)"
FONT_SIZE_2XL = "var(--font-size-2xl)"
FONT_SIZE_3XL = "var(--font-size-3xl)"
FONT_SIZE_4XL = "var(--font-size-4xl)"

SPACE_0 = "var(--space-0)"
SPACE_1 = "var(--space-1)"
SPACE_2 = "var(--space-2)"
SPACE_3 = "var(--space-3)"
SPACE_4 = "var(--space-4)"
SPACE_5 = "var(--space-5)"
SPACE_6 = "var(--space-6)"
SPACE_8 = "var(--space-8)"
SPACE_10 = "var(--space-10)"
SPACE_12 = "var(--space-12)"

RADIUS_NONE = "var(--radius-none)"
RADIUS_SM = "var(--radius-sm)"
RADIUS_MD = "var(--radius-md)"
RADIUS_LG = "var(--radius-lg)"

BORDER_WIDTH = "var(--border-width)"
BORDER_COLOR = "var(--color-border)"


def inject_css(ui) -> None:
    """Inject the Swiss Style CSS into a Streamlit UI object.

    Call this once at the top of the Streamlit app entry point.
    Accepts either the real `streamlit` module or a test double that
    implements `markdown(body, unsafe_allow_html=...)`.
    """
    ui.markdown(f"<style>{CSS_VARIABLES}</style>", unsafe_allow_html=True)


def source_label(source: str) -> str:
    """Return a source label that never implies live broker data.

    Uses semantic HTML with the broker_feed source class so it can be
    styled consistently across all surfaces.
    """
    return {
        "synthetic_fixture": "synthetic fixture — not live broker data",
        "imported_history": "imported history — not live broker data",
        "broker_feed": "broker feed — read-only, not live orders",
    }.get(source, f"{source} — not live broker data")


def health_badge(status: str) -> tuple[str, str]:
    """Return (text, icon) for a health status.

    Colors are never the only signal — text/icon included.
    """
    return {
        "healthy": ("healthy", "✓"),
        "degraded": ("degraded", "⚠"),
        "blocked": ("blocked", "✗"),
    }.get(status, (status, "•"))


def gate_badge(state: str) -> tuple[str, str]:
    """Return (text, icon-key) for a validation gate state.

    States: PASS, FAIL, BLOCKED, NOT RUN (design.md §2 Validation).
    """
    return {
        "PASS": ("PASS", "pass"),
        "FAIL": ("FAIL", "fail"),
        "BLOCKED": ("BLOCKED", "blocked"),
        "NOT RUN": ("NOT RUN", "not_run"),
    }.get(state, (state, "unknown"))


def format_pct(value: float) -> str:
    """Format a percentage with precise units, trimming trailing zeros."""
    return f"{value:g}%"