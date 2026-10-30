"""M11.4 — Streamlit app entry point for the local quant dashboard.

Wires all 8 dashboard surfaces (overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles) behind a sidebar navigation.

State is backend-driven (superbot.m11.api.STATE). Charts use Plotly
(superbot.m11.charts). Every value is labeled internal simulation /
research — never live broker data. Binds localhost only.
"""

from __future__ import annotations

import streamlit as st

from superbot.m11 import ui as m11_ui

PAGES = {
    "Overview": m11_ui.render_overview,
    "Market / Data Explorer": m11_ui.render_data_explorer,
    "Research Queue": m11_ui.render_research_queue,
    "Strategy / Signal Workbench": m11_ui.render_strategy_workbench,
    "Validation / Experiments": m11_ui.render_validation_experiments,
    "Portfolio / Risk (Internal Simulation)": m11_ui.render_portfolio_risk,
    "Audit / Experiment Library": m11_ui.render_audit_library,
    "Settings / Profiles": m11_ui.render_settings_profiles,
}


def main() -> None:
    st.set_page_config(
        page_title="Superbot — Local Quant Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.sidebar.title("Superbot")
    st.sidebar.caption("Local-first research, validation & simulation workstation")
    st.sidebar.divider()
    selection = st.sidebar.radio("Navigate", list(PAGES.keys()), index=0)
    st.sidebar.divider()
    st.sidebar.caption("All values: internal simulation / research — not live broker data")
    st.sidebar.caption("No live orders in V1. Localhost only.")

    page_fn = PAGES[selection]
    page_fn()


if __name__ == "__main__":
    main()
