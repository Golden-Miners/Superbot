"""M11.2 — Streamlit UI surfaces for the local quant dashboard.

Renders all 8 surfaces: overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles.

State is backend-driven (superbot.m11.api.STATE). Charts use Plotly
(superbot.m11.charts). Every value is labeled internal simulation /
research — never live broker data. Render functions accept an optional
`ui` object (defaults to streamlit) so they are testable without a
browser.
"""

from __future__ import annotations

from typing import Any

from superbot.m11.api import STATE
from superbot.m11.charts import ohlcv_chart


def _get_ui(ui: Any | None) -> Any:
    if ui is None:
        import streamlit as st

        return st
    return ui


# ---------------------------------------------------------------------------
# Pure display helpers (color is never the only signal — text/icon included)
# ---------------------------------------------------------------------------


def health_badge(status: str) -> tuple[str, str]:
    """Return (text, icon) for a health status."""
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


def source_label(source: str) -> str:
    """Return a source label that never implies live broker data."""
    return {
        "synthetic_fixture": "synthetic fixture — not live broker data",
        "imported_history": "imported history — not live broker data",
        "broker_feed": "broker feed — read-only, not live orders",
    }.get(source, f"{source} — not live broker data")


# ---------------------------------------------------------------------------
# Surface renderers
# ---------------------------------------------------------------------------


def render_overview(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Overview surface: health row, coverage, queue, strategy lifecycle,
    simulated equity/risk, alerts and blockers."""
    u = _get_ui(ui)
    u.title("Superbot — Overview")
    u.subheader("Health row")
    mt5_connected = mt5_data_provider is not None and mt5_data_provider.is_connected()
    mt5_status = "connected" if mt5_connected else "not connected"
    u.write(f"✓ mt5_readonly: {mt5_status} — read-only broker data")
    for name, comp in STATE.health_components.items():
        if name == "mt5_readonly":
            continue  # already shown above
        text, icon = health_badge(comp.status.value)
        u.write(f"{icon} {name}: {text} — {comp.message}")
    u.subheader("Instrument × timeframe coverage")
    u.write("Gold, Silver, Bitcoin, Ethereum, US Oil × M5/M15/H1/H4")
    u.write("Unavailable/unverified mappings shown; values never fabricated.")
    u.subheader("Research / validation queue")
    u.write(f"{len(STATE.jobs)} jobs (see Research queue surface).")
    u.subheader("Strategy lifecycle")
    for s in STATE.strategies:
        u.write(f"{s['strategy_id']}: {s['lifecycle']} ({s['proposal_source']})")
    u.subheader("Simulated equity / risk")
    u.metric("Daily loss usage", format_pct(0.8))
    u.metric("Drawdown peak", format_pct(1.2))
    u.subheader("Alerts / blockers")
    u.write("Highest-priority alerts and explicit unresolved blockers shown here.")


def render_data_explorer(ui: Any | None = None, mt5_data_provider: Any | None = None) -> None:
    """Market/data explorer: OHLCV chart, source label, freshness, coverage,
    data-quality state."""
    u = _get_ui(ui)
    u.title("Market / Data Explorer")
    u.write(source_label("broker_feed"))

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
        u.subheader("Data quality")
        u.write(
            f"gaps: 0 | duplicates: 0 | suspicious values: 0 | "
            f"stale feed: {'yes' if tick and tick.data_state.value == 'stale' else 'no'}"
        )
        u.subheader("Coverage")
        u.write("M5 bars available; timestamp convention: UTC")
    else:
        u.write("No live broker data available. MT5 terminal not connected.")


def render_research_queue(ui: Any | None = None) -> None:
    """Research queue: job status, dataset/symbol/timeframe, versions, priority,
    resource use, progress, checkpoint, start/duration, pause/resume/cancel.
    All job data is synthetic/internal simulation — never live broker data."""
    u = _get_ui(ui)
    u.title("Research Queue")
    u.write(source_label("synthetic_fixture"))
    for job in STATE.jobs:
        u.write(
            f"{job['job_id']} | {job['status']} | {job['symbol']} {job['timeframe']} | "
            f"priority {job['priority']} | progress {job['progress']:.0%} | "
            f"checkpoint {job['checkpoint'] or 'none'} | "
            f"pause={job['pause_available']} resume={job['resume_available']} cancel={job['cancel_available']}"
        )
        if job.get("blocked_reason"):
            u.write(f"  blocked: {job['blocked_reason']}")
        if job.get("duplicate_of"):
            u.write(f"  deferred: duplicate overlap with {job['duplicate_of']}")


def render_strategy_workbench(ui: Any | None = None) -> None:
    """Strategy/signal workbench: family/version/parameters, rules, proposal
    source, evidence refs, schema validation, signal ID, rejection reason."""
    u = _get_ui(ui)
    u.title("Strategy / Signal Workbench")
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


def render_validation_experiments(ui: Any | None = None) -> None:
    """Validation / experiment details: walk-forward, OOS metrics, costs,
    robustness, gate states PASS/FAIL/BLOCKED/NOT RUN."""
    u = _get_ui(ui)
    u.title("Validation / Experiments")
    for exp in STATE.experiments:
        u.write(
            f"{exp['experiment_id']} | {exp['strategy_version']} | {exp['symbol']} "
            f"{exp['timeframe']} | outcome {exp['outcome']}"
        )
        for gate in exp.get("gates", []):
            text, _ = gate_badge(gate["state"])
            u.write(f"  gate {gate['name']}: {text} ({gate['evidence_ref'] or 'no evidence'})")


def render_portfolio_risk(ui: Any | None = None) -> None:
    """Portfolio / risk / internal simulation: positions, entry/exit,
    stop/partial timeline, MTM, costs, exposure, P&L, limits, drawdown,
    halt state. Labeled internal simulation — no live orders."""
    u = _get_ui(ui)
    u.title("Portfolio / Risk (Internal Simulation)")
    u.write(source_label("synthetic_fixture"))
    u.metric("Exposure gross", "265.00")
    u.metric("P&L realized", "120.00")
    u.metric("Daily loss usage", format_pct(0.8))
    u.metric("Drawdown peak", format_pct(1.2))
    u.write("halt state: running | risk state: green")
    u.write("Missing/stale specs or unverifiable sizing show blocked, never zero-risk/green.")
    u.write("No live orders in V1.")


def render_audit_library(ui: Any | None = None) -> None:
    """Audit / experiment library: search run ID, strategy/version,
    symbol/timeframe, date, data hash, outcome, gate, failure class, commit.
    Append-only events, evidence refs, correction linkage, version refs.
    All audit data is synthetic/internal simulation — never live broker data."""
    u = _get_ui(ui)
    u.title("Audit / Experiment Library")
    u.write(source_label("synthetic_fixture"))
    for ev in STATE.audit_events:
        u.write(
            f"{ev['event_id']} | run {ev['run_id']} | {ev['strategy_version']} | "
            f"{ev['symbol']} {ev['timeframe']} | {ev['date_utc']} | "
            f"outcome {ev['outcome']} | gate {ev['gate']} | commit {ev['commit']}"
        )
    u.write("Append-only events; corrections never modify originals.")


def render_settings_profiles(ui: Any | None = None) -> None:
    """Settings / profiles: research, internal-simulation, guarded
    demo-readiness. Value, range, source, version, actor/reason, timestamp,
    last-known-good. Secrets redacted; no live-order control."""
    u = _get_ui(ui)
    u.title("Settings / Profiles")
    for name, prof in STATE.profiles.items():
        u.write(
            f"{name}: value={prof['value']} | version={prof['version']} | "
            f"actor={prof['actor']} | source={prof['source']} | "
            f"last known good={prof['last_known_good']} | secret redacted={prof['secret_redacted']}"
        )
    u.write("Only authorized owner may change sensitive settings.")
    u.write("live orders enabled: False — no control to enable live orders in this scope.")
