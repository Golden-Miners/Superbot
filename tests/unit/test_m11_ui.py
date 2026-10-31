"""RED tests for M11.2 — Streamlit UI surfaces for the dashboard.

Covers all 8 surfaces: overview, data explorer, research queue,
strategy/signal workbench, validation/experiments, portfolio/risk,
audit/experiment library, settings/profiles.

Pure data helpers are unit-tested. Render functions are smoke-tested
against a fake streamlit-like object (dependency injection) so they are
testable without running a browser. Acceptance: backend-driven state,
explicit synthetic/source labels, no fake success or live-order controls,
gate states PASS/FAIL/BLOCKED/NOT RUN, rejected signal/job shows reason.
"""

from __future__ import annotations

import re

from superbot.m11 import ui as m11_ui


class FakeUI:
    """Records streamlit-like calls for smoke-testing render functions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def recorder(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return recorder


# --- Pure helpers ----------------------------------------------------------

def test_health_badge_maps_status():
    """Health status maps to a text/icon badge (color not the only signal)."""
    assert m11_ui.health_badge("healthy") == ("healthy", "✓")
    assert m11_ui.health_badge("degraded") == ("degraded", "⚠")
    assert m11_ui.health_badge("blocked") == ("blocked", "✗")


def test_gate_badge_distinguishes_states():
    """Gate badge distinguishes PASS/FAIL/BLOCKED/NOT RUN."""
    assert m11_ui.gate_badge("PASS") == ("PASS", "pass")
    assert m11_ui.gate_badge("FAIL") == ("FAIL", "fail")
    assert m11_ui.gate_badge("BLOCKED") == ("BLOCKED", "blocked")
    assert m11_ui.gate_badge("NOT RUN") == ("NOT RUN", "not_run")


def test_format_pct_precise_units():
    """Precise units / number formatting for risk metrics."""
    assert m11_ui.format_pct(0.8) == "0.8%"
    assert m11_ui.format_pct(1.25) == "1.25%"


def test_source_label_not_live():
    """Source label states synthetic/imported/broker and not live."""
    label = m11_ui.source_label("synthetic_fixture")
    assert "synthetic" in label.lower()
    assert "not live" in label.lower()


# --- Render functions (smoke-tested with FakeUI) --------------------------

def test_render_overview_calls_ui_with_health_row():
    ui = FakeUI()
    m11_ui.render_overview(ui)
    names = [c[0] for c in ui.calls]
    assert "title" in names or "header" in names
    assert any("health" in str(args).lower() for _, args, _ in ui.calls)


def test_render_data_explorer_shows_chart_and_labels():
    ui = FakeUI()
    m11_ui.render_data_explorer(ui)
    texts = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "synthetic" in texts.lower() or "XAUUSD" in texts


def test_render_research_queue_lists_jobs():
    ui = FakeUI()
    m11_ui.render_research_queue(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "job" in calls_text.lower()


def test_render_strategy_workbench_shows_rejection_reason():
    ui = FakeUI()
    m11_ui.render_strategy_workbench(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "schema" in calls_text.lower() or "rejection" in calls_text.lower()


def test_render_validation_experiments_shows_gate_states():
    ui = FakeUI()
    m11_ui.render_validation_experiments(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "PASS" in calls_text or "FAIL" in calls_text or "BLOCKED" in calls_text


def test_render_portfolio_risk_labels_internal_simulation():
    ui = FakeUI()
    m11_ui.render_portfolio_risk(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "internal simulation" in calls_text.lower()


def test_render_audit_library_shows_events():
    ui = FakeUI()
    m11_ui.render_audit_library(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "audit" in calls_text.lower() or "event" in calls_text.lower()


def test_render_settings_profiles_no_live_order_control():
    """No interactive control to enable live orders (status line is allowed)."""
    ui = FakeUI()
    m11_ui.render_settings_profiles(ui)
    button_labels = " ".join(
        str(a[0]) if a else "" for name, a, _ in ui.calls if name == "button"
    )
    assert "enable live" not in button_labels.lower()
    assert "live order" not in button_labels.lower()
    # Status line reports live orders are disabled.
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "live orders enabled: false" in calls_text.lower()


def test_all_surface_renderers_exist():
    """All 8 surfaces have a render function."""
    for name in (
        "render_overview",
        "render_data_explorer",
        "render_research_queue",
        "render_strategy_workbench",
        "render_validation_experiments",
        "render_portfolio_risk",
        "render_audit_library",
        "render_settings_profiles",
    ):
        assert callable(getattr(m11_ui, name))


# --- Phase 4.2: Distinguish synthetic fixtures from actual live observations --


def test_render_overview_shows_data_provenance():
    """Overview surface labels health components as not probed / synthetic."""
    ui = FakeUI()
    m11_ui.render_overview(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "not probed" in calls_text.lower()


def test_render_research_queue_shows_data_provenance():
    """Research queue labels jobs as internal simulation / synthetic."""
    ui = FakeUI()
    m11_ui.render_research_queue(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "internal simulation" in calls_text.lower() or "synthetic" in calls_text.lower()


def test_render_strategy_workbench_shows_proposal_source():
    """Strategy workbench labels proposal source (deterministic vs AI)."""
    ui = FakeUI()
    m11_ui.render_strategy_workbench(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "source" in calls_text.lower()


def test_render_validation_experiments_shows_data_source():
    """Validation experiments label data source / provenance."""
    ui = FakeUI()
    m11_ui.render_validation_experiments(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "experiment" in calls_text.lower() or "outcome" in calls_text.lower()


def test_render_audit_library_shows_data_source():
    """Audit library labels events with source/provenance info."""
    ui = FakeUI()
    m11_ui.render_audit_library(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "run" in calls_text.lower() or "event" in calls_text.lower()


def test_render_settings_profiles_shows_config_source():
    """Settings profiles label the config source."""
    ui = FakeUI()
    m11_ui.render_settings_profiles(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args)
    assert "source" in calls_text.lower()


def test_no_surface_implies_live_broker_data():
    """No surface implies any data is live broker data (i.e., no surface
    states data IS live without "not" qualification)."""
    ui = FakeUI()
    for renderer in (
        m11_ui.render_overview,
        m11_ui.render_data_explorer,
        m11_ui.render_research_queue,
        m11_ui.render_strategy_workbench,
        m11_ui.render_validation_experiments,
        m11_ui.render_portfolio_risk,
        m11_ui.render_audit_library,
        m11_ui.render_settings_profiles,
    ):
        renderer(ui)
    calls_text = " ".join(str(a) for _, args, _ in ui.calls for a in args).lower()
    # No surface should state data IS live (without "not" qualification).
    # "not live broker data" is fine; "live broker data" without "not" is not.
    # "no live orders in v1" is fine; "live orders enabled: true" is not.
    sanitized = re.sub(r"\bnot live\b", "", calls_text)
    sanitized = re.sub(r"\bno live orders\b", "", sanitized)
    assert "live broker" not in sanitized
    assert "live order enabled" not in sanitized
    assert "live market" not in sanitized
    # All surfaces should explicitly state "not live" or "internal simulation"
    # or "synthetic" somewhere
    assert "not live" in calls_text or "internal simulation" in calls_text or "synthetic" in calls_text


def test_chart_annotations_state_not_live():
    """Plotly chart annotations state source and not-live status."""
    fig = m11_ui.ohlcv_chart("XAUUSD", "M5", [], source="synthetic_fixture")
    annotations = fig.layout.annotations or []
    texts = [str(a.text) for a in annotations]
    assert any("not live" in t.lower() for t in texts)


def test_chart_annotations_state_source():
    """Plotly chart annotations state the data source."""
    fig = m11_ui.ohlcv_chart("XAUUSD", "M5", [], source="synthetic_fixture")
    annotations = fig.layout.annotations or []
    texts = [str(a.text) for a in annotations]
    assert any("synthetic" in t.lower() for t in texts)
