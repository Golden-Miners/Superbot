"""RED tests for M11.1 — Select UI/API/chart stack using inspection + ADR.

Tests define:
- UIStackSelection: documents the chosen UI framework, API framework, chart library
- UIStack: registry of the selected stack (ui_framework, api_framework, chart_library, packaging)
- StackDecision: records inspected version, license, runtime, requirements, suitability, accept/reject reason
- ADR file at docs/adr/0004-ui-api-chart-stack.md with Status: Accepted
- ADR documents rationale, alternatives considered, consequences
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from superbot.m11.ui_stack import (
    StackDecision,
    UIStack,
    UIStackSelection,
    load_adr,
    load_ui_stack,
    ui_stack,
)


def test_ui_stack_creates():
    """UIStack can be created with all three layers."""
    stack = UIStack(
        ui_framework="streamlit",
        api_framework="fastapi",
        chart_library="plotly",
        packaging="pip",
    )
    assert stack.ui_framework == "streamlit"
    assert stack.api_framework == "fastapi"
    assert stack.chart_library == "plotly"
    assert stack.packaging == "pip"


def test_ui_stack_selection_creates():
    """UIStackSelection documents the decision."""
    stack = UIStack(
        ui_framework="streamlit",
        api_framework="fastapi",
        chart_library="plotly",
        packaging="pip",
    )
    selection = UIStackSelection(stack=stack, rationale="Python-first, localhost-only")
    assert selection.stack == stack
    assert "python" in selection.rationale.lower()


def test_stack_decision_records_version_license():
    """StackDecision records inspected version, license, runtime, requirements."""
    decision = StackDecision(
        component="chart_library",
        name="plotly",
        version="5.22.0",
        license="MIT",
        runtime="python",
        requirements=["plotly"],
        suitability="high",
        accept=True,
        reason="Python-native, integrates with Streamlit, no build step",
    )
    assert decision.name == "plotly"
    assert decision.version == "5.22.0"
    assert decision.license == "MIT"
    assert decision.accept is True


def test_load_ui_stack_returns_selection():
    """load_ui_stack returns the selected stack."""
    stack = load_ui_stack()
    assert stack is not None
    assert stack.ui_framework
    assert stack.api_framework
    assert stack.chart_library


def test_ui_stack_constant():
    """ui_stack module-level constant exposes the selected stack."""
    assert ui_stack is not None
    assert ui_stack.ui_framework == "streamlit"
    assert ui_stack.api_framework == "fastapi"
    assert ui_stack.chart_library == "plotly"


def test_load_adr_exists():
    """load_adr reads the ADR file and returns its content."""
    adr = load_adr()
    assert adr is not None
    assert "accepted" in adr.lower()
    assert "streamlit" in adr.lower()
    assert "fastapi" in adr.lower()
    assert "plotly" in adr.lower()


def test_adr_has_status_accepted():
    """ADR file has Status: Accepted."""
    adr = load_adr()
    assert "**status:** accepted" in adr.lower() or "status: accepted" in adr.lower()


def test_adr_documents_rationale():
    """ADR documents the rationale for the selection."""
    adr = load_adr()
    assert "rationale" in adr.lower()


def test_adr_documents_alternatives():
    """ADR documents alternatives considered."""
    adr = load_adr()
    assert "alternative" in adr.lower()


def test_adr_documents_consequences():
    """ADR documents consequences of the decision."""
    adr = load_adr()
    assert "consequence" in adr.lower()


def test_adr_records_inspected_version():
    """ADR records the inspected version of each component."""
    adr = load_adr()
    assert "version" in adr.lower()


def test_adr_records_inspected_license():
    """ADR records the inspected license of each component."""
    adr = load_adr()
    assert "license" in adr.lower()


def test_ui_stack_deterministic():
    """Same inputs yield identical stack selection."""
    s1 = load_ui_stack()
    s2 = load_ui_stack()
    assert s1.ui_framework == s2.ui_framework
    assert s1.api_framework == s2.api_framework
    assert s1.chart_library == s2.chart_library
