"""RED tests for M6.3 — PF/Sharpe/Sortino/DD/trade-count gates with documented conventions.

Tests define:
- GateSpec: versioned gate configuration with explicit PF/Sharpe/Sortino/max DD/trade-count thresholds
- Gate evaluation against BaselineMetrics from M5.4
- All gates pass → PASS; any gate fails → FAIL with documented reason
- Documented conventions: each threshold has an explicit rationale
- Gate aggregation: multiple gate results combined
- Failing gates block (no model can set PASS directly)
- Deterministic: same inputs → same gate result
- Threshold boundaries: exactly at threshold passes (>= / <= convention)
- Baseline with zero trades cannot pass (insufficient evidence)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.strategy.gates import (
    GateSpec,
    GateVerdict,
    evaluate_gates,
)


def test_gate_spec_versioned():
    """GateSpec carries schema_version and spec_id with explicit thresholds."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_001",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.spec_id == "gate_001"


def test_gates_pass_when_all_thresholds_met():
    """All gates pass when metrics exceed every threshold."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_pass",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.4"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 20,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.PASS
    assert result.failures == []


def test_gates_fail_when_profit_factor_below_threshold():
    """Profit factor below threshold fails with documented reason."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_pf_fail",
        min_pf=Decimal("2.0"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal("1.5"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.4"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 20,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.FAIL
    assert "min_pf" in result.failures


def test_gates_fail_when_drawdown_exceeds_threshold():
    """Max drawdown above threshold fails with documented reason."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_dd_fail",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(5),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.4"),
        "max_dd_pct": Decimal(8),
        "win_rate_pct": Decimal(60),
        "trade_count": 20,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.FAIL
    assert "max_dd_pct" in result.failures


def test_gates_fail_when_trade_count_below_threshold():
    """Trade count below threshold fails (insufficient evidence)."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_count_fail",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=30,
    )
    metrics = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.4"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 10,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.FAIL
    assert "min_trade_count" in result.failures


def test_threshold_boundary_passes():
    """Exactly at threshold passes (>= / <= convention)."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_boundary",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal("1.5"),
        "sharpe": Decimal("1.0"),
        "sortino": Decimal("1.0"),
        "max_dd_pct": Decimal(10),
        "win_rate_pct": Decimal(40),
        "trade_count": 10,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.PASS
    assert result.failures == []


def test_zero_trades_cannot_pass():
    """Zero trades cannot pass (insufficient evidence regardless of metrics)."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_zero_trades",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal(999999),
        "sharpe": Decimal(999999),
        "sortino": Decimal(999999),
        "max_dd_pct": Decimal(0),
        "win_rate_pct": Decimal(100),
        "trade_count": 0,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.FAIL
    assert "min_trade_count" in result.failures


def test_deterministic_gate_result():
    """Same inputs yield identical gate result."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_det",
        min_pf=Decimal("1.5"),
        min_sharpe=Decimal("1.0"),
        min_sortino=Decimal("1.0"),
        max_dd_pct=Decimal(10),
        min_win_rate_pct=Decimal(40),
        min_trade_count=10,
    )
    metrics = {
        "pf": Decimal("2.0"),
        "sharpe": Decimal("1.5"),
        "sortino": Decimal("1.4"),
        "max_dd_pct": Decimal(5),
        "win_rate_pct": Decimal(60),
        "trade_count": 15,
    }
    r1 = evaluate_gates(metrics, spec)
    r2 = evaluate_gates(metrics, spec)
    assert r1.verdict == r2.verdict
    assert r1.failures == r2.failures


def test_multiple_gate_failures_all_reported():
    """Multiple failing gates all reported, not just first."""
    spec = GateSpec(
        schema_version="1.0.0",
        spec_id="gate_multi_fail",
        min_pf=Decimal("2.0"),
        min_sharpe=Decimal("2.0"),
        min_sortino=Decimal("2.0"),
        max_dd_pct=Decimal(5),
        min_win_rate_pct=Decimal(50),
        min_trade_count=20,
    )
    metrics = {
        "pf": Decimal("1.0"),
        "sharpe": Decimal("0.5"),
        "sortino": Decimal("0.4"),
        "max_dd_pct": Decimal(15),
        "win_rate_pct": Decimal(30),
        "trade_count": 5,
    }
    result = evaluate_gates(metrics, spec)
    assert result.verdict == GateVerdict.FAIL
    assert len(result.failures) == 6  # all six gates fail


def test_gate_spec_decimal_fields_must_be_decimal():
    """Decimal fields must be Decimal values."""
    with pytest.raises(ValueError):
        GateSpec(
            schema_version="1.0.0",
            spec_id="gate_bad_decimal",
            min_pf="not_a_decimal",
            min_sharpe=Decimal("1.0"),
            min_sortino=Decimal("1.0"),
            max_dd_pct=Decimal(10),
            min_win_rate_pct=Decimal(40),
            min_trade_count=10,
        )
