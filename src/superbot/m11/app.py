"""M11.4 — Streamlit app entry point for the local quant dashboard.

Wires all 8 dashboard surfaces (overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles) behind a sidebar navigation.

State is backend-driven (superbot.m11.api.STATE). Charts use Plotly
(superbot.m11.charts). Every value is labeled internal simulation /
research — never live broker data. Binds localhost only.

Execution permission service and MT5 execution adapter are wired to allow
demo-order execution on a connected MetaTrader5 terminal.
"""

from __future__ import annotations

import streamlit as st

from superbot.m11 import ui as m11_ui
from superbot.m11.design_tokens import inject_css
from superbot.m11.execution_authorizer import (
    ExecutionMode,
    ExecutionPermissionService,
)
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider

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
    inject_css(st)
    st.sidebar.title("Superbot")
    st.sidebar.caption("Local-first research, validation & simulation workstation")
    st.sidebar.divider()
    selection = st.sidebar.radio("Navigate", list(PAGES.keys()), index=0)
    st.sidebar.divider()
    st.sidebar.caption("Local-first research, validation & simulation workstation")
    st.sidebar.caption("Demo execution enabled on MT5. Localhost only.")

    # Connect to MT5 terminal for live market data and order execution
    mt5_provider = MT5DataProvider()
    mt5_connected = mt5_provider.connect()
    st.sidebar.caption(f"MT5 terminal: {'connected' if mt5_connected else 'not connected'}")

    # Setup execution permission service and adapter (persist in session state
    # so execution mode survives Streamlit reruns)
    if 'auth' not in st.session_state:
        auth = ExecutionPermissionService(mt5_data_provider=mt5_provider)
        # Default to READ_ONLY on startup — never auto-enable autonomous execution
        auth.set_mode(ExecutionMode.READ_ONLY)
        st.session_state.auth = auth
    else:
        auth = st.session_state.auth

    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5_provider, auth=auth)

    # Execution mode control — explicit ON/OFF switch only
    st.sidebar.subheader("Execution Control")
    mode = auth.get_mode()

    if mode == ExecutionMode.OFF:
        if st.sidebar.button("Enable Demo Execution", type="primary"):
            from superbot.m11.auth import SessionStore

            ss = SessionStore()
            _sess, token = ss.create_session(role="owner")
            auth.set_mode(ExecutionMode.AUTONOMOUS_DEMO)
            st.sidebar.success("Autonomous demo execution enabled")
            st.rerun()
        st.sidebar.caption("Mode: OFF — no new trade entries")
    elif mode == ExecutionMode.READ_ONLY:
        if st.sidebar.button("Enable Demo Execution", type="primary"):
            from superbot.m11.auth import SessionStore

            ss = SessionStore()
            _sess, token = ss.create_session(role="owner")
            auth.set_mode(ExecutionMode.AUTONOMOUS_DEMO)
            st.sidebar.success("Autonomous demo execution enabled")
            st.rerun()
        st.sidebar.caption("Mode: READ_ONLY — market data and analysis only")
    elif mode == ExecutionMode.AUTONOMOUS_DEMO:
        if st.sidebar.button("Disable Execution", type="secondary"):
            auth.set_mode(ExecutionMode.READ_ONLY)
            st.sidebar.success("Execution disabled — READ_ONLY mode")
            st.rerun()
        st.sidebar.caption("Mode: AUTONOMOUS_DEMO — live demo execution active")
        if st.sidebar.button("Emergency Stop", type="secondary"):
            auth.set_mode(ExecutionMode.OFF)
            st.sidebar.error("Emergency stop activated — OFF mode")
            st.rerun()

    page_fn = PAGES[selection]
    if selection == "Overview":
        page_fn(ui=st, mt5_data_provider=mt5_provider, auth=auth, adapter=adapter)
    elif selection == "Market / Data Explorer":
        page_fn(ui=st, mt5_data_provider=mt5_provider)
    elif selection == "Research Queue":
        page_fn(ui=st, mt5_data_provider=mt5_provider)
    elif selection == "Strategy / Signal Workbench":
        page_fn(ui=st, mt5_data_provider=mt5_provider)
    elif selection == "Validation / Experiments":
        page_fn(ui=st, mt5_data_provider=mt5_provider)
    elif selection == "Portfolio / Risk (Internal Simulation)":
        page_fn(ui=st, mt5_data_provider=mt5_provider, adapter=adapter)
    elif selection == "Audit / Experiment Library":
        page_fn(ui=st, mt5_data_provider=mt5_provider)
    elif selection == "Settings / Profiles":
        page_fn(ui=st, mt5_data_provider=mt5_provider, auth=auth)
    else:
        page_fn(ui=st, mt5_data_provider=mt5_provider)


if __name__ == "__main__":
    main()