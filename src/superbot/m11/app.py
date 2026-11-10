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
from superbot.m11.execution_authorizer import ExecutionPermissionService
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

    # Setup execution permission service and adapter
    auth = ExecutionPermissionService(mt5_data_provider=mt5_provider)
    auth.LIVE_TRADING_ENABLED = True
    adapter = MT5ExecutionAdapter(mt5_data_provider=mt5_provider, auth=auth)

    # Enable execution if MT5 is connected and account is demo
    if mt5_connected:
        from superbot.m11.auth import SessionStore

        session_store = SessionStore()
        _session, token = session_store.create_session(role="owner")
        auth.enable_execution(token, session_store)
        st.sidebar.caption("Execution mode: DEMO_EXECUTION (armed)")
    else:
        st.sidebar.caption("Execution mode: READ_ONLY (MT5 not connected)")

    page_fn = PAGES[selection]
    if selection == "Overview":
        page_fn(mt5_data_provider=mt5_provider, auth=auth, adapter=adapter)
    elif selection == "Market / Data Explorer":
        page_fn(mt5_data_provider=mt5_provider)
    elif selection == "Research Queue":
        page_fn(mt5_data_provider=mt5_provider)
    elif selection == "Strategy / Signal Workbench":
        page_fn(mt5_data_provider=mt5_provider)
    elif selection == "Validation / Experiments":
        page_fn(mt5_data_provider=mt5_provider)
    elif selection == "Portfolio / Risk (Internal Simulation)":
        page_fn(mt5_data_provider=mt5_provider, adapter=adapter)
    elif selection == "Audit / Experiment Library":
        page_fn(mt5_data_provider=mt5_provider)
    elif selection == "Settings / Profiles":
        page_fn(mt5_data_provider=mt5_provider, auth=auth)
    elif selection == "Trade History":
        page_fn(mt5_data_provider=mt5_provider, adapter=adapter)
    else:
        page_fn(mt5_data_provider=mt5_provider)


if __name__ == "__main__":
    main()
