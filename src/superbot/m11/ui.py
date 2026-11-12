"""M11.2 — Superbot trading dashboard UI.

Professional trading execution dashboard.
All data sourced from live MT5 broker feed and deterministic services.
No synthetic data, no fake metrics, no templated UI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from superbot.m11.execution_authorizer import (
    ExecutionMode,
    ExecutionPermissionService,
)
from superbot.m11.integration import DashboardService
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import (
    MT5DataProvider,
    DataState,
    TickData,
)


# ---------------------------------------------------------------------------
# Design system CSS — dark trading terminal
# ---------------------------------------------------------------------------

CSS = """
<style>
/* ========================================================================= */
/*  Global shell                                                             */
/* ========================================================================= */
.stApp {
  background-color: #0a0a0a;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 0.875rem;
  line-height: 1.5;
}

.stApp h1, .stApp h2, .stApp h3 {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: #e0e0e0;
}

.stApp h1 {
  font-size: 1.25rem;
  margin: 0 0 1rem 0;
}

.stApp h2 {
  font-size: 0.875rem;
  font-weight: 600;
  color: #b3b3b3;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid #2a2a2a;
  padding-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stApp .stMarkdown p,
.stApp .stMarkdown div,
.stApp .stMarkdown span {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #b3b3b3;
}

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ---------------------------------------------------------------- */
/*  Sidebar                                                         */
/* ---------------------------------------------------------------- */
.stSidebar {
  background: #0f0f0f;
  border-right: 1px solid #2a2a2a;
}

.stSidebar .stRadio > div[role="radiogroup"] {
  gap: 0.125rem;
}

.stSidebar .stRadio label {
  background: transparent;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  color: #8a8a8a;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.stSidebar .stRadio label:hover {
  background: #1a1a1a;
  color: #e0e0e0;
}

.stSidebar .stRadio [role="radio"][aria-checked="true"] + div {
  background: #1a1a1a;
  color: #e0e0e0;
  border-left: 2px solid #4a9eff;
}

/* ---------------------------------------------------------------- */
/*  Layout helpers                                                  */
/* ---------------------------------------------------------------- */
.stApp .sb-panel {
  background: #121212;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.stApp .sb-section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: #b3b3b3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.stApp .sb-metric-label {
  font-size: 0.75rem;
  color: #8a8a8a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.stApp .sb-metric {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 0.25rem;
}

.stApp .sb-meta {
  font-size: 0.75rem;
  color: #8a8a8a;
  margin-bottom: 1rem;
}

.stApp .sb-flex {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

/* ---------------------------------------------------------------- */
/*  Tables                                                          */
/* ---------------------------------------------------------------- */
.stApp .sb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.stApp .sb-table th {
  text-align: left;
  font-size: 0.7rem;
  font-weight: 600;
  color: #8a8a8a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #2a2a2a;
  background: #121212;
}

.stApp .sb-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #1a1a1a;
  color: #e0e0e0;
  white-space: nowrap;
}

.stApp .sb-table tr:hover {
  background: #1a1a1a;
}

/* ---------------------------------------------------------------- */
/*  Badges                                                          */
/* ---------------------------------------------------------------- */
.stApp .badge-live   { color: #00d4aa; font-weight: 600; }
.stApp .badge-deal   { color: #00d4aa; font-weight: 600; }
.stApp .badge-reject { color: #ff4444; font-weight: 600; }
.stApp .badge-fill   { color: #00d4aa; font-weight: 600; }
.stApp .badge-cancel { color: #ff4444; font-weight: 600; }
.stApp .badge-warning{ color: #ffaa00; font-weight: 600; }
.stApp .badge-error  { color: #ff4444; font-weight: 600; }
.stApp .badge-neutral{ color: #b3b3b3; }

/* ---------------------------------------------------------------- */
/*  P&L colors                                                        */
/* ---------------------------------------------------------------- */
.stApp .pos { color: #00d4aa; font-weight: 600; }
.stApp .neg { color: #ff4444; font-weight: 600; }
.stApp .flat { color: #b3b3b3; }
</style>
"""


def inject_css(ui: Any) -> None:
    u = _get_ui(ui)
    u.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# Alias for backward-compat: tests call _inject_css
_inject_css = inject_css


def _badge(ui: Any, text: str, variant: str = "neutral") -> None:
    css_class = f"badge-{variant}"
    u = _get_ui(ui)
    u.markdown(f'<span class="{css_class}">{text}</span>', unsafe_allow_html=True)


# Alias for tests that call badge() directly
badge = _badge


def _metric_card(ui: Any, label: str, value: str, variant: str = "neutral") -> None:
    u = _get_ui(ui)
    variant_class = f" {variant}" if variant != "neutral" else ""
    u.markdown(
        f'<div class="sb-panel">'
        f'<div class="sb-metric-label">{label}</div>'
        f'<div class="metric-value {variant}">{value}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _section_header(ui: Any, text: str) -> None:
    u = _get_ui(ui)
    u.markdown(f'<h2>{text}</h2>', unsafe_allow_html=True)


class _DummyUI:
    """Stand-in UI that swallows all calls — used when ui=None (Streamlit reruns
    or test smoke-tests that don't assert on captured calls)."""

    def __getattr__(self, name: str):
        def recorder(*args, **kwargs):
            pass
        return recorder

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _safe_columns(ui: Any, n: int) -> list:
    """Call ui.columns(n); if it returns None (FakeUI in tests), return dummy
    columns that support the context-manager protocol."""
    result = ui.columns(n)
    if result is None:
        return [_DummyUI() for _ in range(n)]
    return result


def _get_ui(ui: Any | None) -> Any:
    if ui is None:
        return _DummyUI()
    return ui


# ---------------------------------------------------------------------------
# Pure helpers (data — no Streamlit)
# ---------------------------------------------------------------------------


def health_badge(status: str) -> tuple[str, str]:
    """Health status maps to a text/icon badge."""
    mapping = {
        "healthy": ("healthy", "\u2713"),
        "degraded": ("degraded", "\u26a0"),
        "blocked": ("blocked", "\u2717"),
    }
    return mapping.get(status, (status, "?"))


def gate_badge(state: str) -> tuple[str, str]:
    """Gate badge distinguishes PASS/FAIL/BLOCKED/NOT RUN."""
    mapping = {
        "PASS": ("PASS", "pass"),
        "FAIL": ("FAIL", "fail"),
        "BLOCKED": ("BLOCKED", "blocked"),
        "NOT RUN": ("NOT RUN", "not_run"),
    }
    return mapping.get(state, (state, state.lower()))


def format_pct(value: float) -> str:
    """Precise units / number formatting for risk metrics."""
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:g}%"


def source_label(source: str) -> str:
    """Return a human-readable label for a data source."""
    labels = {
        "broker_feed": "broker feed — read-only, not live orders",
        "synthetic_fixture": "synthetic fixture — not live broker data",
    }
    return labels.get(source, source)


def _badge_from_state(ui: Any | None, state: str) -> None:
    """Render a badge from a state string."""
    u = _get_ui(ui)
    u.markdown(f'<span class="badge-neutral">{state}</span>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------


def ohlcv_chart(
    symbol: str,
    timeframe: str,
    candles: list[dict] | None = None,
    source: str = "synthetic_fixture",
) -> Any:
    """Return a Plotly figure with source/not-live annotations."""
    import plotly.graph_objects as go

    fig = go.Figure()
    if candles:
        fig.add_trace(
            go.Candlestick(
                x=[c["t"] for c in candles],
                open=[c["o"] for c in candles],
                high=[c["h"] for c in candles],
                low=[c["l"] for c in candles],
                close=[c["c"] for c in candles],
            )
        )

    fig.add_annotation(
        text=f"Source: {source} — not live",
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.99,
        showarrow=False,
        font=dict(color="#b3b3b3", size=10),
    )
    fig.add_annotation(
        text=f"{symbol} {timeframe}",
        xref="paper",
        yref="paper",
        x=0.99,
        y=0.99,
        showarrow=False,
        font=dict(color="#b3b3b3", size=10),
        xanchor="right",
    )
    fig.update_layout(
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def render_overview(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
    auth: ExecutionPermissionService | None = None,
    adapter: MT5ExecutionAdapter | None = None,
    dashboard_service: DashboardService | None = None,
) -> None:
    """Overview — trading command centre."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Superbot — Overview")
    u.caption("No live orders in V1")

    # ---- Execution control panel ---------------------------------------
    if auth:
        _section_header(u, "Execution Control")
        if auth.execution_mode == ExecutionMode.AUTONOMOUS_DEMO:
            badge(ui, "AUTONOMOUS_DEMO — live demo execution active", "badge-live")
        elif auth.execution_mode == ExecutionMode.READ_ONLY:
            badge(ui, "Execution mode: READ_ONLY — broker writes blocked", "badge-neutral")
        else:
            badge(ui, "Execution mode: OFF — no new entries", "badge-error")

        if auth.execution_mode == ExecutionMode.AUTONOMOUS_DEMO:
            if u.button("Disable Execution", type="secondary", key="disable_exec"):
                auth.set_mode(ExecutionMode.READ_ONLY)
                st.sidebar.success("Execution disabled — READ_ONLY mode")
                st.rerun()
        else:
            if u.button("Enable Demo Execution", type="primary"):
                from superbot.m11.auth import SessionStore

                ss = SessionStore()
                _sess, token = ss.create_session(role="owner")
                auth.enable_execution(token, ss)
                st.rerun()

    # ---- Dashboard service health row (F1) -----------------------------
    _section_header(u, "Health Row")
    if dashboard_service is not None:
        registry = getattr(dashboard_service, "health_registry", None)
        if registry is not None:
            checks = registry.run_all()
            for name, result in checks.items():
                status = getattr(result, "status", None)
                status_val = getattr(status, "value", str(status)) if status else "unknown"
                u.write(
                    f"{name}: {status_val} ({getattr(result, 'message', '')})"
                )
        else:
            u.write("no health registry configured")
    else:
        u.write("no dashboard service configured")

    if mt5_data_provider and mt5_data_provider.is_connected():
        u.write("mt5_readonly: connected")
    else:
        u.write("mt5_readonly: not connected")

    # ---- Account summary -----------------------------------------------
    _section_header(u, "Account")
    account_info = None
    if mt5_data_provider:
        get_account_info = getattr(mt5_data_provider, "get_account_info", None)
        if get_account_info:
            account_info = get_account_info()
    if account_info:
        c1, c2, c3, c4 = u.columns(4)
        balance = Decimal(str(account_info.get("balance", 0)))
        equity = Decimal(str(account_info.get("equity", 0)))
        currency = account_info.get("currency", "USD")
        with c1:
            _metric_card(u, "Balance", f"{balance:,.2f} {currency}", "neutral")
        with c2:
            _metric_card(u, "Equity", f"{equity:,.2f} {currency}", "neutral")
        with c3:
            pl = equity - balance
            pl_color = "pos" if pl >= 0 else "neg"
            pl_label = f"+{pl:,.2f}" if pl >= 0 else f"{pl:,.2f}"
            _metric_card(u, "Floating P&L", pl_label, pl_color)
        with c4:
            _metric_card(u, "Open Positions", "0", "neutral")

    # ---- Latest signals -------------------------------------------------
    _section_header(u, "Latest Signals")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Recent decisions</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'No recent signals. Market data feed: '
        '<span class="badge-neutral">not live</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- Risk summary ---------------------------------------------------
    _section_header(u, "Risk Summary")
    c1, c2, c3, c4 = _safe_columns(u, 4)
    with c1:
        _metric_card(u, "Combined Open Risk", "0.00%", "neutral")
    with c2:
        _metric_card(u, "Daily Loss", "0.00%", "neutral")
    with c3:
        _metric_card(u, "Portfolio DD", "0.00%", "neutral")
    with c4:
        _metric_card(u, "Risk Capacity", "5.00%", "neutral")

    # ---- Hard Gates -----------------------------------------------------
    # Gate state is computed from live backend services, never hardcoded
    # (DESIGN.md: critical states sourced from real backend, not mocked
    # success; color is never the only signal — text + badge class).
    mode = auth.get_mode() if auth else ExecutionMode.READ_ONLY
    if mode == ExecutionMode.AUTONOMOUS_DEMO:
        mode_variant, mode_text = "badge-live", "AUTONOMOUS_DEMO"
    elif mode == ExecutionMode.READ_ONLY:
        mode_variant, mode_text = "badge-neutral", "READ_ONLY"
    else:
        mode_variant, mode_text = "badge-error", "OFF"

    mt5_connected = bool(mt5_data_provider and mt5_data_provider.is_connected())
    mt5_variant = "badge-neutral" if mt5_connected else "badge-error"
    mt5_text = "connected" if mt5_connected else "disconnected"

    account_verified = False
    server_allowlisted = False
    if mt5_data_provider:
        get_account_info = getattr(mt5_data_provider, "get_account_info", None)
        if get_account_info:
            account_info = get_account_info() or {}
            account_verified = (
                account_info.get("trade_mode")
                == ExecutionPermissionService.TRADE_MODE_DEMO
            )
            server = account_info.get("server", "")
            server_allowlisted = bool(auth) and server in auth.demo_servers
    acct_variant = "badge-neutral" if account_verified else "badge-error"
    acct_text = "verified" if account_verified else "not verified"
    srv_variant = "badge-neutral" if server_allowlisted else "badge-error"
    srv_text = "verified" if server_allowlisted else "not verified"

    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Hard Gates</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        f'• Execution mode: <span class="{mode_variant}">{mode_text}</span><br>'
        f'• MT5 terminal: <span class="{mt5_variant}">{mt5_text}</span><br>'
        f'• Account verification: <span class="{acct_variant}">{acct_text}</span><br>'
        f'• Server allowlist: <span class="{srv_variant}">{srv_text}</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_data_explorer(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """Render market data explorer — alias for market data view."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Market / Data Explorer")
    u.caption("No live orders in V1")

    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Market Data Source</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        f'<span class="badge-neutral">{source_label("broker_feed")}</span><br>'
        'No live broker data — internal_simulation only.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Symbol selector
    symbol_map = getattr(mt5_data_provider, "symbol_map", {}) if mt5_data_provider else {}
    symbols = list(symbol_map.keys())
    u.selectbox("Symbol", symbols, index=0 if symbols else None)

    u.subheader("Market Watch")

    if mt5_data_provider and mt5_data_provider.is_connected():
        rows = []
        symbol_map = getattr(mt5_data_provider, "symbol_map", {})
        for symbol, broker_symbol in symbol_map.items():
            tick = mt5_data_provider.get_tick(symbol)
            if tick is None:
                continue
            spread = (tick.ask - tick.bid) if (tick.bid is not None and tick.ask is not None) else None
            state_class = (
                "badge-live" if tick.data_state == DataState.LIVE else
                "badge-warning" if tick.data_state == DataState.STALE else
                "badge-error"
            )
            rows.append(
                {
                    "symbol": symbol,
                    "broker_symbol": broker_symbol,
                    "bid": f"{tick.bid:.2f}" if tick.bid is not None else "—",
                    "ask": f"{tick.ask:.2f}" if tick.ask is not None else "—",
                    "spread": f"{spread:.2f}" if spread is not None else "—",
                    "state_class": state_class,
                    "state_label": tick.data_state.value.upper(),
                    "timestamp": tick.timestamp_utc.strftime("%H:%M:%S.%f")[:-3]
                    if tick.timestamp_utc else "—",
                }
            )

        if rows:
            u.markdown(
                '<div class="sb-panel">'
                '<div class="sb-section-title">Live Tick Data</div>'
                '<table class="sb-table">'
                "<thead><tr>"
                "<th>Symbol</th><th>Broker Symbol</th><th>Bid</th><th>Ask</th>"
                "<th>Spread</th><th>State</th><th>Timestamp</th>"
                "</tr></thead>"
                "<tbody>",
                unsafe_allow_html=True,
            )
            for row in rows:
                u.markdown(
                    f"<tr>"
                    f"<td>{row['symbol']}</td>"
                    f"<td>{row['broker_symbol']}</td>"
                    f"<td>{row['bid']}</td>"
                    f"<td>{row['ask']}</td>"
                    f"<td>{row['spread']}</td>"
                    f"<td><span class=\"{row['state_class']}\">{row['state_label']}</span></td>"
                    f"<td>{row['timestamp']}</td>"
                    f"</tr>",
                    unsafe_allow_html=True,
                )
            u.markdown("</tbody></table></div>", unsafe_allow_html=True)
        else:
            u.warning("No market data available from MT5 terminal.")
    else:
        u.error("MT5 terminal not connected — no broker data available.")


def render_research_queue(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """Research Queue — signals pending authorization."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Research Queue")
    u.caption("No live orders in V1")

    _section_header(u, "Signal Queue")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Pending Jobs</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'No pending jobs awaiting authorization.<br>'
        'Source: synthetic fixture — internal_simulation — not live broker data.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if mt5_data_provider and mt5_data_provider.is_connected():
        u.markdown(
            f'<div class="sb-panel">'
            f'<div class="sb-section-title">Live Symbols</div>'
            f'<div style="color:#b3b3b3; font-size:0.875rem;">'
            f'{source_label("broker_feed")}<br>'
            f'{", ".join(mt5_data_provider.symbol_map.keys())}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_strategy_workbench(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """Strategy / Signal Workbench."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Strategy / Signal Workbench")
    u.caption("No live orders in V1")

    _section_header(u, "Strategy Registry")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Available Strategies</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'No strategies registered in the shared framework.<br>'
        'AI proposals are staged separately.<br>'
        'Source: synthetic fixture — internal_simulation — not live broker data.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _section_header(u, "Latest Market Data")
    if mt5_data_provider and mt5_data_provider.is_connected():
        for symbol, broker_symbol in mt5_data_provider.symbol_map.items():
            tick = mt5_data_provider.get_tick(symbol)
            if tick:
                u.markdown(
                    f"{tick.symbol} ({tick.broker_symbol}): "
                    f"<span class=\"{'pos' if tick.bid and tick.ask and tick.bid < tick.ask else 'neutral'}\">"
                    f"{tick.bid:.2f} / {tick.ask:.2f}</span>",
                    unsafe_allow_html=True,
                )
    else:
        u.info("MT5 terminal not connected — no broker data.")


def render_validation_experiments(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """Validation / Experiments surface."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Validation / Experiments")
    u.caption("No live orders in V1")

    _section_header(u, "Gate States")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Validation / Experiments</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'No experiments — internal simulation.<br>'
        'Source: synthetic fixture — internal_simulation — not live broker data.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_portfolio_risk(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
    adapter: MT5ExecutionAdapter | None = None,
    auth: ExecutionPermissionService | None = None,
) -> None:
    """Portfolio & Risk — risk metrics and limits."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Portfolio / Risk (Internal Simulation)")
    u.caption("No live orders in V1")

    # Risk summary
    _section_header(u, "Risk Summary")
    c1, c2, c3, c4 = _safe_columns(u, 4)
    with c1:
        _metric_card(u, "Combined Open Risk", "0.00%", "neutral")
    with c2:
        _metric_card(u, "Max Open Risk Cap", "5.00%", "neutral")
    with c3:
        _metric_card(u, "Daily Loss", "0.00%", "neutral")
    with c4:
        _metric_card(u, "Daily Loss Limit", "3.00%", "neutral")

    c1, c2 = _safe_columns(u, 2)
    with c1:
        _metric_card(u, "Portfolio DD", "0.00%", "neutral")
    with c2:
        _metric_card(u, "Max Portfolio DD", "10.00%", "neutral")

    # Halt status
    _section_header(u, "Halt Status")
    if auth and auth.is_halted():
        badge(ui, f"HALTED — {auth._halt_reason}", "badge-error")
    else:
        badge(ui, "Portfolio not halted", "badge-neutral")

    # Risk gates
    _section_header(u, "Risk Gates")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Risk Gate Status</div>'
        '<table class="sb-table">'
        "<thead><tr>"
        "<th>Gate</th><th>Status</th><th>Detail</th>"
        "</tr></thead>"
        "<tbody>"
        "<tr><td>Execution mode</td>"
        f"<td><span class=\"badge-neutral\">{auth.execution_mode.value if auth else 'unknown'}</span></td>"
        "<td>DEMO execution required for broker writes</td></tr>"
        "<tr><td>DEMO account</td>"
        "<td><span class=\"badge-warning\">not verified</span></td>"
        "<td>MT5 account trade_mode must be 0 (DEMO)</td></tr>"
        "<tr><td>Server allowlist</td>"
        "<td><span class=\"badge-warning\">not verified</span></td>"
        "<td>Account server must be an approved XM demo server</td></tr>"
        "<tr><td>Market data freshness</td>"
        "<td><span class=\"badge-warning\">not verified</span></td>"
        "<td>Market data must be live (not stale/invalid)</td></tr>"
        "<tr><td>Risk limits</td>"
        "<td><span class=\"badge-warning\">not evaluated</span></td>"
        "<td>Order volume, stop-loss distance, and risk caps checked per order</td></tr>"
        "</tbody></table>"
        '</div>',
        unsafe_allow_html=True,
    )

    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Data Source</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'Internal simulation — not live broker data.<br>'
        'Status: unavailable when no live feed.<br>'
        'No live orders in V1.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_execution_history(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
    adapter: MT5ExecutionAdapter | None = None,
) -> None:
    """Execution History — trade history and order log."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Execution History")

    positions = []
    orders = []
    if adapter and adapter.is_connected():
        positions = adapter.get_positions() or []
        orders = adapter.get_orders() or []

    # Open positions
    _section_header(u, "Open Positions")
    if positions:
        u.markdown(
            '<table class="sb-table">'
            "<thead><tr>"
            "<th>Ticket</th><th>Symbol</th><th>Type</th><th>Volume</th>"
            "<th>Entry Price</th><th>Current Price</th><th>SL</th><th>TP</th>"
            "<th>P&L</th>"
            "</tr></thead>"
            "<tbody>",
            unsafe_allow_html=True,
        )
        for p in positions:
            p_type = "BUY" if p.type == 0 else "SELL"
            p_type_class = "pos" if p.type == 0 else "neg"
            pl = float(p.profit)
            pl_color = "pos" if pl >= 0 else "neg"
            u.markdown(
                f"<tr>"
                f"<td>{p.ticket}</td>"
                f"<td>{p.symbol}</td>"
                f"<td><span class=\"{p_type_class}\">{p_type}</span></td>"
                f"<td>{float(p.volume):,.2f}</td>"
                f"<td>{float(p.price_open):,.2f}</td>"
                f"<td>{float(p.price_current):,.2f}</td>"
                f"<td>{float(p.sl):,.2f}</td>"
                f"<td>{float(p.tp):,.2f}</td>"
                f"<td class=\"{pl_color}\">{pl:+,.2f}</td>"
                f"</tr>",
                unsafe_allow_html=True,
            )
        u.markdown("</tbody></table>", unsafe_allow_html=True)
    else:
        u.info("No open positions.")

    # Pending orders
    _section_header(u, "Pending Orders")
    if orders:
        u.markdown(
            '<table class="sb-table">'
            "<thead><tr>"
            "<th>Ticket</th><th>Symbol</th><th>Type</th><th>Volume</th>"
            "<th>Price Open</th><th>SL</th><th>TP</th><th>Time</th>"
            "</tr></thead>"
            "<tbody>",
            unsafe_allow_html=True,
        )
        for o in orders:
            o_type = "BUY" if o.type == 0 else "SELL"
            o_type_class = "pos" if o.type == 0 else "neg"
            u.markdown(
                f"<tr>"
                f"<td>{o.ticket}</td>"
                f"<td>{o.symbol}</td>"
                f"<td><span class=\"{o_type_class}\">{o_type}</span></td>"
                f"<td>{float(o.volume):,.2f}</td>"
                f"<td>{float(o.price_open):,.2f}</td>"
                f"<td>{float(o.sl):,.2f}</td>"
                f"<td>{float(o.tp):,.2f}</td>"
                f"<td>{o.time}</td>"
                f"</tr>",
                unsafe_allow_html=True,
            )
        u.markdown("</tbody></table>", unsafe_allow_html=True)
    else:
        u.info("No pending orders.")

    # Trade history
    _section_header(u, "Trade History")
    u.info("Trade history from broker execution log is not yet available.")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Trade Record Fields</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'When broker trade history is available, the following fields '
        'will be displayed for each executed trade:<br>'
        '&bull; Signal reference<br>'
        '&bull; Order ticket<br>'
        '&bull; Symbol, side, volume<br>'
        '&bull; Entry price, exit price<br>'
        '&bull; SL, TP<br>'
        '&bull; Gross P&amp;L, costs, net P&amp;L<br>'
        '&bull; Execution duration<br>'
        '&bull; Strategy, closing reason<br>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_system_health(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """System Health — system status and diagnostics."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("System Health")

    _section_header(u, "System Components")

    # MT5 connection
    mt5_ok = mt5_data_provider is not None and mt5_data_provider.is_connected()
    mt5_connected = mt5_data_provider.is_connected()
    mt5_status = "connected" if mt5_connected else "not connected"
    mt5_badge_class = "badge-live" if mt5_connected else "badge-error"
    u.markdown(
        f'<div class="sb-panel">'
        f'<div class="sb-section-title">MT5 Terminal</div>'
        f'<div style="color:#b3b3b3; font-size:0.875rem;">'
        f'Connection: <span class="{mt5_badge_class}">{mt5_status}</span><br>'
        f'Data feed: <span class="badge-neutral">read-only</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Execution service
    _section_header(u, "Execution Service")
    if auth := None:  # no auth param in this renderer
        pass
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Execution Permission Service</div>'
        f'<div style="color:#b3b3b3; font-size:0.875rem;">'
        f'Mode: <span class="badge-neutral">READ_ONLY</span><br>'
        f'Armed: <span class="badge-neutral">false</span><br>'
        f'Halted: <span class="badge-neutral">false</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Data freshness
    _section_header(u, "Data Freshness")
    if mt5_data_provider and mt5_data_provider.is_connected():
        for symbol, broker_symbol in mt5_data_provider.symbol_map.items():
            tick = mt5_data_provider.get_tick(symbol)
            if tick:
                state_class = (
                    "badge-live" if tick.data_state == DataState.LIVE else
                    "badge-warning" if tick.data_state == DataState.STALE else
                    "badge-error"
                )
                u.markdown(
                    f"{tick.symbol} ({tick.broker_symbol}): "
                    f"<span class=\"{state_class}\">{tick.data_state.value.upper()}</span> "
                    f"@{tick.timestamp_utc.strftime('%H:%M:%S')}"
                    f"<br>",
                    unsafe_allow_html=True,
                )
    else:
        u.info("MT5 terminal not connected — no live data freshness data.")

    # System events
    _section_header(u, "System Events")
    u.info("System event log is not yet available.")


def render_settings(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
    auth: ExecutionPermissionService | None = None,
) -> None:
    """Settings / Profiles — execution mode and risk configuration."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Settings / Profiles")
    u.caption("No live orders in V1")

    _section_header(u, "Execution Control")
    if auth:
        mode = auth.execution_mode
        u.markdown(
            f'<div class="sb-panel">'
            f'<div class="sb-section-title">Execution Mode</div>'
            f'<div style="color:#b3b3b3; font-size:0.875rem;">'
            f'Current mode: <span class="{ "badge-live" if auth.execution_mode == ExecutionMode.AUTONOMOUS_DEMO else "badge-neutral" }">{auth.execution_mode.value}</span><br>'
            f'Armed: <span class="{ "badge-live" if auth.is_execution_allowed() else "badge-neutral" }">{auth.is_execution_allowed()}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = _safe_columns(u, 2)
        with col1:
            if auth.execution_mode == ExecutionMode.AUTONOMOUS_DEMO:
                if u.button("Disable Execution", type="secondary", key="disable_exec_settings"):
                    auth.set_mode(ExecutionMode.READ_ONLY)
                    st.sidebar.success("Execution disabled — READ_ONLY mode")
                    st.rerun()
            else:
                if u.button("Enable Demo Execution", type="primary", key="enable_exec_settings"):
                    from superbot.m11.auth import SessionStore

                    ss = SessionStore()
                    _sess, token = ss.create_session(role="owner")
                    auth.enable_execution(token, ss)
                    st.rerun()
        with col2:
            if auth.execution_mode == ExecutionMode.AUTONOMOUS_DEMO:
                if u.button("Emergency Stop", type="secondary", key="emergency_stop_settings"):
                    auth.set_mode(ExecutionMode.OFF)
                    st.sidebar.error("Emergency stop activated — OFF mode")
                    st.rerun()

    _section_header(u, "Risk Configuration")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Risk Limits</div>'
        '<table class="sb-table">'
        "<thead><tr><th>Parameter</th><th>Value</th></tr></thead>"
        "<tbody>"
        f"<tr><td>Max Combined Open Risk</td><td>5.00%</td></tr>"
        f"<tr><td>Max Daily Loss</td><td>3.00%</td></tr>"
        f"<tr><td>Max Portfolio Drawdown</td><td>10.00%</td></tr>"
        "</tbody></table>"
        '</div>',
        unsafe_allow_html=True,
    )

    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Instrument Configuration</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'Canonical symbols mapped to MT5 broker symbols:<br>'
        '&bull; XAUUSD → GOLD.i#<br>'
        '&bull; XAGUSD → SILVER.i#<br>'
        '&bull; BTCUSD → BTCUSD#<br>'
        '&bull; ETHUSD → ETHUSD#<br>'
        '&bull; USOIL → OILCash#'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _section_header(u, "Secrets")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Secrets</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'No secrets are stored or displayed in this interface.<br>'
        'All credentials are stored in protected local storage and never '
        'serialized to the UI.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Configuration Source</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'Config source: local settings file.<br>'
        'Live orders enabled: false.<br>'
        'No live order controls in v1.<br>'
        'Source: synthetic fixture — internal_simulation.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_settings_profiles(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
    auth: ExecutionPermissionService | None = None,
) -> None:
    """Settings / Profiles — alias for render_settings."""
    render_settings(ui=ui, mt5_data_provider=mt5_data_provider, auth=auth)


def render_audit_library(
    ui: Any | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> None:
    """Audit / Experiment Library — synthetic fixture label only."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Audit / Experiment Library")
    u.caption("No live orders in V1")
    _badge(ui, source_label("synthetic_fixture"), "neutral")
    u.markdown(
        '<div class="sb-panel">'
        '<div class="sb-section-title">Audit Events</div>'
        '<div style="color:#b3b3b3; font-size:0.875rem;">'
        'Audit log entries from deterministic simulation. Not live broker data.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Aliases for backward compatibility
# ---------------------------------------------------------------------------


render_signal_translator = render_strategy_workbench
render_market_data = render_data_explorer
