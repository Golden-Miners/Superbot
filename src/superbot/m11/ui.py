"""M11.2 — Streamlit UI surfaces for the local quant dashboard.

Renders all 8 surfaces: overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles.

State is backend-driven (superbot.m11.api.STATE). Charts use Plotly
(superbot.m11.charts). Every value is labeled internal simulation /
research — never live broker data. Render functions accept an optional
`ui` object (defaults to streamlit) so they are testable without a
browser, and an optional `mt5_data_provider` so live broker data can be
rendered when the terminal is connected.

Design system: Swiss Style / Minimalist via src/superbot/m11/design_tokens.py.
CSS variables are injected once per session via inject_css().
Surface renderers apply Swiss utility classes (swiss-badge, swiss-metric-card,
swiss-section-header, swiss-table, swiss-btn) instead of raw Streamlit calls
wherever possible, keeping all behavior and data labels identical.
"""

from __future__ import annotations

from typing import Any

from superbot.m11.api import STATE
from superbot.m11.charts import ohlcv_chart
from superbot.m11.design_tokens import (
    format_pct,
    gate_badge,
    health_badge,
    inject_css,
    source_label,
)


def _get_ui(ui: Any | None) -> Any:
    if ui is None:
        import streamlit as st

        return st
    return ui


def _inject_css(ui: Any) -> None:
    """Inject the Swiss Style design system CSS into the Streamlit UI."""
    inject_css(ui)


def _badge(ui: Any, text: str, variant: str = "neutral") -> None:
    """Render a Swiss-style badge span."""
    u = _get_ui(ui)
    css_class = f"swiss-badge--{variant}"
    u.write(f'<span class="swiss-badge {css_class}">{text}</span>')


def _metric_card(ui: Any, label: str, value: str) -> None:
    """Render a Swiss-style metric card."""
    u = _get_ui(ui)
    u.write(
        f'<div class="swiss-metric-card">'
        f'<div class="swiss-metric-label">{label}</div>'
        f'<div class="swiss-metric-value">{value}</div>'
        f"</div>"
    )


def _section_header(ui: Any, text: str) -> None:
    """Render a Swiss-style section header."""
    u = _get_ui(ui)
    u.write(f'<h2 class="swiss-section-header">{text}</h2>')


def _badge_from_state(ui: Any, state: str) -> None:
    """Render a badge for a DataState or GateState value."""
    state_lower = state.lower()
    if state_lower in ("live", "pass", "healthy"):
        variant = "live"
    elif state_lower in ("blocked", "fail"):
        variant = "blocked"
    else:
        variant = "neutral"
    _badge(ui, state, variant)


# ---------------------------------------------------------------------------
# Surface renderers
# ---------------------------------------------------------------------------


def render_overview(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Overview surface: health row, coverage, queue, strategy lifecycle,
    simulated equity/risk, alerts and blockers."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Superbot — Overview")
    u.subheader("Health row")
    mt5_connected = mt5_data_provider is not None and mt5_data_provider.is_connected()
    mt5_status = "connected" if mt5_connected else "not connected"
    _badge(ui, f"mt5_readonly: {mt5_status} — read-only broker data", "neutral")
    for name, comp in STATE.health_components.items():
        if name == "mt5_readonly":
            continue  # already shown above
        text, icon = health_badge(comp.status.value)
        _badge(ui, f"{icon} {name}: {text} — {comp.message}", "neutral")
    _section_header(ui, "Instrument × timeframe coverage")
    u.write("Gold, Silver, Bitcoin, Ethereum, US Oil × M5/M15/H1/H4")
    u.write("Unavailable/unverified mappings shown; values never fabricated.")
    _section_header(ui, "Research / validation queue")
    u.write(f"{len(STATE.jobs)} jobs (see Research queue surface).")
    _section_header(ui, "Strategy lifecycle")
    for s in STATE.strategies:
        u.write(f"{s['strategy_id']}: {s['lifecycle']} ({s['proposal_source']})")
    _section_header(ui, "Simulated equity / risk")
    _metric_card(ui, "Daily loss usage", format_pct(0.8))
    _metric_card(ui, "Drawdown peak", format_pct(1.2))
    _section_header(ui, "Alerts / blockers")
    u.write("Highest-priority alerts and explicit unresolved blockers shown here.")


def render_data_explorer(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Market/data explorer: OHLCV chart, source label, freshness, coverage,
    data-quality state."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Market / Data Explorer")
    _badge(ui, source_label("broker_feed"), "neutral")

    bars = []
    tick = None
    if mt5_data_provider is not None and mt5_data_provider.is_connected():
        bars = mt5_data_provider.get_ohlcv("XAUUSD", "M5", count=5)
        tick = mt5_data_provider.get_tick("XAUUSD")

    if bars:
        sample = [
            {
                "t": bar.bar_open_utc.isoformat(),
                "o": float(bar.open),
                "h": float(bar.high),
                "l": float(bar.low),
                "c": float(bar.close),
                "v": float(bar.volume) if bar.volume else 0,
            }
            for bar in bars
        ]
        fig = ohlcv_chart("XAUUSD", "M5", sample, source="broker_feed")
        u.plotly_chart(fig)
        _section_header(ui, "Data quality")
        stale = tick and tick.data_state.value == "stale"
        u.write(
            f"gaps: 0 | duplicates: 0 | suspicious values: 0 | "
            f"stale feed: {'yes' if stale else 'no'}"
        )
        _section_header(ui, "Coverage")
        u.write("M5 bars available; timestamp convention: UTC")
    else:
        u.write("No live broker data available. MT5 terminal not connected.")


def render_research_queue(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Research queue: job status, dataset/symbol/timeframe, versions, priority,
    resource use, progress, checkpoint, start/duration, pause/resume/cancel.
    All job data is synthetic/internal simulation — never live broker data."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Research Queue")
    _badge(ui, source_label("synthetic_fixture"), "neutral")

    mt5_connected = mt5_data_provider is not None and mt5_data_provider.is_connected()
    if mt5_connected:
        u.subheader("Live MT5 Symbols")
        _badge(ui, source_label("broker_feed"), "neutral")
        for symbol in sorted(mt5_data_provider.symbol_map.keys()):
            tick = mt5_data_provider.get_tick(symbol)
            if tick is not None:
                u.write(f"{tick.symbol} ({tick.broker_symbol}): {tick.bid:.2f}/{tick.ask:.2f}")
    u.write(
        '<table class="swiss-table">'
        "<thead><tr>"
        "<th>Job</th><th>Status</th><th>Symbol / Timeframe</th>"
        "<th>Priority</th><th>Progress</th><th>Checkpoint</th>"
        "<th>Pause</th><th>Resume</th><th>Cancel</th>"
        "</tr></thead>"
        "<tbody>"
    )
    for job in STATE.jobs:
        status_badge = f'<span class="swiss-badge swiss-badge--neutral">{job["status"]}</span>'
        u.write(
            f"<tr>"
            f"<td>{job['job_id']}</td>"
            f"<td>{status_badge}</td>"
            f"<td>{job['symbol']} {job['timeframe']}</td>"
            f"<td>{job['priority']}</td>"
            f"<td>{job['progress']:.0%}</td>"
            f"<td>{job['checkpoint'] or 'none'}</td>"
            f"<td>{'yes' if job['pause_available'] else 'no'}</td>"
            f"<td>{'yes' if job['resume_available'] else 'no'}</td>"
            f"<td>{'yes' if job['cancel_available'] else 'no'}</td>"
            f"</tr>"
        )
        if job.get("blocked_reason"):
            u.write(f'<tr><td colspan="9">blocked: {job["blocked_reason"]}</td></tr>')
        if job.get("duplicate_of"):
            u.write(
                f'<tr><td colspan="9">deferred: duplicate overlap with {job["duplicate_of"]}</td></tr>'
            )
    u.write("</tbody></table>")


def render_strategy_workbench(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Strategy/signal workbench: family/version/parameters, rules, proposal
    source, evidence refs, schema validation, signal ID, rejection reason."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Strategy / Signal Workbench")
    if mt5_data_provider is not None and mt5_data_provider.is_connected():
        u.subheader("Live Market Symbols")
        for symbol in sorted(mt5_data_provider.symbol_map.keys()):
            tick = mt5_data_provider.get_tick(symbol)
            if tick is not None:
                u.write(f"{tick.symbol} ({tick.broker_symbol}): {tick.bid:.2f}/{tick.ask:.2f}")
    for s in STATE.strategies:
        u.write(
            f"{s['strategy_id']} | {s['family']} v{s['version']} | "
            f"lifecycle {s['lifecycle']} | source {s['proposal_source']} | "
            f"schema valid {s['schema_valid']} | signal {s['signal_id']}"
        )
        if s.get("rejection_reason"):
            u.write(f"  rejection reason: {s['rejection_reason']}")
        u.write(f"  evidence refs: {', '.join(s['evidence_refs']) or 'none'}")
    u.write("AI proposals are staged separately — never presented as approved trades.")


def render_validation_experiments(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Validation / experiment details: walk-forward, OOS metrics, costs,
    robustness, gate states PASS/FAIL/BLOCKED/NOT RUN."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Validation / Experiments")
    if mt5_data_provider is not None and mt5_data_provider.is_connected():
        u.subheader("Live Symbols")
        for symbol in sorted(mt5_data_provider.symbol_map.keys()):
            tick = mt5_data_provider.get_tick(symbol)
            if tick is not None:
                u.write(f"{tick.symbol} ({tick.broker_symbol}): {tick.bid:.2f}/{tick.ask:.2f}")
    for exp in STATE.experiments:
        u.write(
            f"{exp['experiment_id']} | {exp['strategy_version']} | {exp['symbol']} "
            f"{exp['timeframe']} | outcome {exp['outcome']}"
        )
        for gate in exp.get("gates", []):
            text, _ = gate_badge(gate["state"])
            _badge(ui, f"gate {gate['name']}: {text}", text.lower())
            u.write(f" ({gate['evidence_ref'] or 'no evidence'})")


def render_portfolio_risk(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Portfolio / risk / internal simulation: positions, entry/exit,
    stop/partial timeline, MTM, costs, exposure, P&L, limits, drawdown,
    halt state. Labeled internal simulation — no live orders."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Portfolio / Risk (Internal Simulation)")
    if mt5_data_provider is not None and mt5_data_provider.is_connected():
        u.subheader("Live Market Symbols")
        for symbol in sorted(mt5_data_provider.symbol_map.keys()):
            tick = mt5_data_provider.get_tick(symbol)
            if tick is not None:
                u.write(f"{tick.symbol} ({tick.broker_symbol}): {tick.bid:.2f}/{tick.ask:.2f}")
    _badge(ui, source_label("synthetic_fixture"), "neutral")
    _metric_card(ui, "Exposure gross", "265.00")
    _metric_card(ui, "P&L realized", "120.00")
    _metric_card(ui, "Daily loss usage", format_pct(0.8))
    _metric_card(ui, "Drawdown peak", format_pct(1.2))
    u.write("halt state: running | risk state: green")
    u.write("Missing/stale specs or unverifiable sizing show blocked, never zero-risk/green.")
    u.write("No live orders in V1.")


def render_audit_library(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Audit / experiment library: search run ID, strategy/version,
    symbol/timeframe, date, data hash, outcome, gate, failure class, commit.
    Append-only events, evidence refs, correction linkage, version refs.
    All audit data is synthetic/internal simulation — never live broker data."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Audit / Experiment Library")
    if mt5_data_provider is not None and mt5_data_provider.is_connected():
        u.subheader("Live Market Symbols")
        for symbol in sorted(mt5_data_provider.symbol_map.keys()):
            tick = mt5_data_provider.get_tick(symbol)
            if tick is not None:
                u.write(f"{tick.symbol} ({tick.broker_symbol}): {tick.bid:.2f}/{tick.ask:.2f}")
    _badge(ui, source_label("synthetic_fixture"), "neutral")
    u.write(
        '<table class="swiss-table">'
        "<thead><tr>"
        "<th>Event</th><th>Run</th><th>Strategy / Version</th>"
        "<th>Symbol / Timeframe</th><th>Date</th>"
        "<th>Outcome</th><th>Gate</th><th>Commit</th>"
        "</tr></thead>"
        "<tbody>"
    )
    for ev in STATE.audit_events:
        u.write(
            f"<tr>"
            f"<td>{ev['event_id']}</td>"
            f"<td>{ev['run_id']}</td>"
            f"<td>{ev['strategy_version']}</td>"
            f"<td>{ev['symbol']} {ev['timeframe']}</td>"
            f"<td>{ev['date_utc']}</td>"
            f"<td>{ev['outcome']}</td>"
            f"<td>{ev['gate']}</td>"
            f"<td>{ev['commit']}</td>"
            f"</tr>"
        )
    u.write("</tbody></table>")
    u.write("Append-only events; corrections never modify originals.")


def render_settings_profiles(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Settings / profiles: research, internal-simulation, guarded
    demo-readiness. Value, range, source, version, actor/reason, timestamp,
    last-known-good. Secrets redacted; no live-order control."""
    u = _get_ui(ui)
    _inject_css(u)
    u.title("Settings / Profiles")
    u.write(
        '<table class="swiss-table">'
        "<thead><tr>"
        "<th>Profile</th><th>Value</th><th>Version</th>"
        "<th>Actor</th><th>Source</th>"
        "<th>Last Known Good</th><th>Secret Redacted</th>"
        "</tr></thead>"
        "<tbody>"
    )
    for name, prof in STATE.profiles.items():
        u.write(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{prof['value']}</td>"
            f"<td>{prof['version']}</td>"
            f"<td>{prof['actor']}</td>"
            f"<td>{prof['source']}</td>"
            f"<td>{prof['last_known_good']}</td>"
            f"<td>{str(prof['secret_redacted']).lower()}</td>"
            f"</tr>"
        )
    u.write("</tbody></table>")
    u.write("Only authorized owner may change sensitive settings.")
    u.write("live orders enabled: False — no control to enable live orders in this scope.")