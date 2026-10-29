"""RED tests for M3.5 — Assess alternative engine only for a demonstrated capability gap.

Tests define:
- Engine capability matrix: custom baseline, NautilusTrader, LEAN
- Capability gap assessment: is there a demonstrated capability gap requiring another engine?
- Alternative engine assessment: only proceed if a demonstrated gap exists
- If no gap, record that no alternative engine is needed
"""

from __future__ import annotations

from superbot.engine.engine_assessment import (
    EngineCapability,
    EngineAssessment,
    AlternativeEngineAssessment,
)


def test_engine_capability_matrix():
    """Engine capability matrix covers all three POC'd engines."""
    matrix = EngineCapability()
    assert "custom_baseline" in matrix.engines
    assert "nautilus_trader" in matrix.engines
    assert "lean" in matrix.engines


def test_capability_gap_assessment_no_gap():
    """No capability gap when all three engines are functional."""
    assessment = EngineAssessment()
    assessment.register_engine("custom_baseline", "custom", True)
    assessment.register_engine("nautilus_trader", "event_driven", True)
    assessment.register_engine("lean", "event_driven", True)
    result = assessment.assess_gap()
    assert result.gap_detected is False
    assert result.reason == "no_alternative_engine_needed"


def test_alternative_engine_not_needed_when_no_gap():
    """Alternative engine assessment returns not needed when no gap."""
    assessment = AlternativeEngineAssessment()
    result = assessment.assess()
    assert result.alternative_needed is False
    assert result.reason == "no_capability_gap"


def test_alternative_engine_required_when_gap():
    """Alternative engine required when gap detected."""
    assessment = AlternativeEngineAssessment()
    assessment.register_gap("real_time_execution")
    result = assessment.assess()
    assert result.alternative_needed is True
    assert "real_time_execution" in result.missing_capabilities
