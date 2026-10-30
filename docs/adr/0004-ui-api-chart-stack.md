# ADR-004: UI/API/chart stack for the local quant dashboard

**Status:** Accepted  
**Date:** 2026-10-30  
**Scope:** M11.1 — Select UI/API/chart stack using inspection + ADR

## Decision

Select the following stack for the Superbot local quant dashboard and operator API:

| Layer | Selection | Version | License | Runtime | Accept |
|-------|-----------|---------|---------|---------|--------|
| UI framework | Streamlit | current (2026) | Apache-2.0 | Python | Yes |
| API framework | FastAPI | current (2026) | MIT | Python | Yes |
| Chart library | Plotly | current (2026) | MIT | Python | Yes |
| Packaging | pip via pyproject.toml | — | — | Python | Yes |

The selected stack is exposed in `src/superbot/m11/ui_stack.py` as `ui_stack`
(`UIStack(ui_framework="streamlit", api_framework="fastapi",
chart_library="plotly", packaging="pip")`).

## Rationale

- **Python-first / local-first:** All three selections are Python-native packages
  installable via pip with no Node/JavaScript build step, matching the project's
  Python-first, Windows-native, local-first principles (PRD §2, §14; architecture
  §2). This keeps the dependency surface small and offline-capable.
- **Localhost-only binding:** Streamlit and FastAPI both bind to localhost by
  default, satisfying the requirement that the dashboard/API bind locally and
  never expose unauthenticated public endpoints (architecture §10; PRD §4).
- **No build step:** Streamlit renders UI from Python; Plotly renders charts from
  Python. This avoids a separate frontend toolchain, keeping the feedback loop
  local and offline, consistent with the package-layout ADR (ADR-001).
- **Integration:** Plotly integrates directly with Streamlit, so charts render
  without a custom JS bridge. FastAPI serves the backend API that Streamlit
  consumes over localhost.
- **Dashboard fit:** Streamlit's component ecosystem (tables, metrics, charts,
  sidebar controls) maps cleanly to the design brief's surfaces (overview,
  market/data explorer with OHLCV chart, research queue, strategy/signal
  workbench, validation/experiment details, portfolio/risk, audit/experiment
  library, settings/profiles).
- **Chart candidate evaluated:** `tradingview/lightweight-charts` was considered
  per architecture §10 but rejected for V1 because it requires a separate JS
  build/bundling step and a custom Streamlit component wrapper, adding
  dependency and maintenance surface. Plotly provides equivalent OHLCV/line
  charting in pure Python with no build step. lightweight-charts may be
  reconsidered if a custom Streamlit component is later justified by evidence.

## Alternatives considered

- **Streamlit + FastAPI + Plotly (selected):** Python-native, localhost-only,
  no build step, good dashboard fit.
- **FastAPI + lightweight-charts + custom JS frontend:** Rejected — requires a
  Node/JavaScript build step and custom Streamlit/component wrapper; adds
  dependency surface and contradicts the Python-first, no-build-step preference.
- **Streamlit + Streamlit-native charts only:** Rejected — Streamlit's built-in
  `st.line_chart`/`st.area_chart` are too limited for OHLCV candlestick charts
  with overlays required by the market/data explorer; Plotly is needed.
- **Desktop GUI (PyQt/PySide/Tkinter):** Rejected — adds windowing complexity,
  packaging overhead, and does not fit the browser-based dashboard model in the
  design brief.

## Consequences

- New UI code lives under `src/superbot/ui/` (per the package-layout ADR), with
  FastAPI routes under `src/superbot/api/` and chart helpers under
  `src/superbot/ui/charts/`.
- Streamlit, FastAPI and Plotly are added as optional dev/runtime dependencies
  in `pyproject.toml` under an optional `[project.optional-dependencies] ui`
  group; they are not part of the stdlib-only foundation.
- The dashboard binds to localhost by default; remote access, if ever enabled,
  uses an approved private VPN only (never direct public exposure).
- All chart values are labelled as internal-simulation/research or synthetic
  fixture; no value is presented as live broker data (design §2, §3).
- The decision is recorded here; any later stack change requires a new ADR and
  migration of UI/API/chart code.
