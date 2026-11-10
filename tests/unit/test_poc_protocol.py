"""RED tests for M3.7a — standardized POC protocol.

Covers:
- POCProtocol validation
- POCRunResult outlier detection
- POCEvidence aggregation (pass rate, median latency, acceptance criteria)
- RepresentativeDataset deterministic generation
- StressDataset gap-through-stop fixture
- run_poc_protocol: warm-up + measured repetitions, correctness gate,
  noise/additional-run rule, acceptance criteria

Stdlib-only. No import-time network, MT5, database, or model activity.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.engine.poc_protocol import (
    POCEvidence,
    POCProtocol,
    POCRunResult,
    RepresentativeDataset,
    StressDataset,
    run_poc_protocol,
)

# --- POCProtocol validation ---


def test_protocol_defaults_are_valid():
    """Default protocol configuration is valid."""
    p = POCProtocol()
    assert p.is_valid() is True


def test_protocol_requires_non_negative_warmup():
    """warm_up_count must be >= 0."""
    p = POCProtocol(warm_up_count=-1)
    assert p.is_valid() is False


def test_protocol_requires_at_least_one_repetition():
    """measured_repetition_count must be >= 1."""
    p = POCProtocol(measured_repetition_count=0)
    assert p.is_valid() is False


def test_protocol_requires_non_negative_noise_tolerance():
    """noise_tolerance_pct must be >= 0."""
    p = POCProtocol(noise_tolerance_pct=Decimal("-1.0"))
    assert p.is_valid() is False


def test_protocol_requires_valid_pass_rate():
    """min_pass_rate must be > 0 and <= 100."""
    p = POCProtocol(min_pass_rate=Decimal(0))
    assert p.is_valid() is False
    p = POCProtocol(min_pass_rate=Decimal(101))
    assert p.is_valid() is False


# --- POCRunResult outlier detection ---


def test_run_result_outlier_high_latency():
    """Run is outlier when latency deviates from baseline by > tolerance."""
    run = POCRunResult(
        repetition=1,
        engine="custom_baseline",
        fixture="canonical_10bar",
        correctness_gate_passed=True,
        passed=True,
        reason="",
        latency_ms=Decimal(100),
        event_count=3,
    )
    baseline = Decimal(50)
    tolerance = Decimal(50)  # 50% tolerance
    assert run.is_outlier(baseline, tolerance) is True


def test_run_result_within_tolerance_is_not_outlier():
    """Run is not outlier when deviation <= tolerance."""
    run = POCRunResult(
        repetition=1,
        engine="custom_baseline",
        fixture="canonical_10bar",
        correctness_gate_passed=True,
        passed=True,
        reason="",
        latency_ms=Decimal(70),
        event_count=3,
    )
    baseline = Decimal(50)
    tolerance = Decimal(50)  # 50% tolerance
    assert run.is_outlier(baseline, tolerance) is False


def test_run_result_zero_baseline_not_outlier():
    """Zero baseline latency never flags outlier."""
    run = POCRunResult(
        repetition=1,
        engine="custom_baseline",
        fixture="canonical_10bar",
        correctness_gate_passed=True,
        passed=True,
        reason="",
        latency_ms=Decimal(1000),
        event_count=3,
    )
    assert run.is_outlier(Decimal(0), Decimal(10)) is False


# --- POCEvidence aggregation ---


def test_evidence_pass_rate_all_passed():
    """Pass rate is 100% when all runs pass."""
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10),
            event_count=3,
        )
        for i in range(5)
    )
    ev = POCEvidence(protocol=POCProtocol(), engine="custom_baseline", results=results)
    assert ev.pass_rate == Decimal(100)


def test_evidence_pass_rate_some_failed():
    """Pass rate reflects failures."""
    results = (
        POCRunResult(
            repetition=1,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10),
            event_count=3,
        ),
        POCRunResult(
            repetition=2,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=False,
            passed=False,
            reason="correctness gate failed",
            latency_ms=Decimal(10),
            event_count=3,
        ),
    )
    ev = POCEvidence(protocol=POCProtocol(), engine="custom_baseline", results=results)
    assert ev.pass_rate == Decimal(50)


def test_evidence_all_correctness_passed():
    """all_correctness_passed is True when every run passes correctness."""
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10),
            event_count=3,
        )
        for i in range(3)
    )
    ev = POCEvidence(protocol=POCProtocol(), engine="custom_baseline", results=results)
    assert ev.all_correctness_passed is True


def test_evidence_median_latency():
    """Median latency is the middle value of sorted latencies."""
    latencies = [Decimal(10), Decimal(20), Decimal(30), Decimal(40), Decimal(50)]
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=latencies[i],
            event_count=3,
        )
        for i in range(5)
    )
    ev = POCEvidence(protocol=POCProtocol(), engine="custom_baseline", results=results)
    assert ev.median_latency_ms == Decimal(30)


def test_evidence_median_latency_even_count():
    """Median latency for even count is average of two middle values."""
    latencies = [Decimal(10), Decimal(20), Decimal(30), Decimal(40)]
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=latencies[i],
            event_count=3,
        )
        for i in range(4)
    )
    ev = POCEvidence(protocol=POCProtocol(), engine="custom_baseline", results=results)
    assert ev.median_latency_ms == Decimal(25)


def test_evidence_meets_acceptance_all_passed():
    """Evidence meets acceptance when all runs pass within criteria."""
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10),
            event_count=3,
        )
        for i in range(5)
    )
    ev = POCEvidence(
        protocol=POCProtocol(correctness_required_on_all_repetitions=True),
        engine="custom_baseline",
        results=results,
    )
    assert ev.meets_acceptance_criteria() is True


def test_evidence_fails_acceptance_when_correctness_fails():
    """Evidence fails acceptance when any correctness gate fails."""
    results = (
        POCRunResult(
            repetition=1,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=False,
            passed=False,
            reason="correctness failed",
            latency_ms=Decimal(10),
            event_count=3,
        ),
    ) + tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10),
            event_count=3,
        )
        for i in range(2, 6)
    )
    ev = POCEvidence(
        protocol=POCProtocol(correctness_required_on_all_repetitions=True),
        engine="custom_baseline",
        results=results,
    )
    assert ev.meets_acceptance_criteria() is False


def test_evidence_fails_acceptance_when_latency_exceeds_max():
    """Evidence fails acceptance when median latency exceeds max."""
    results = tuple(
        POCRunResult(
            repetition=i,
            engine="custom_baseline",
            fixture="canonical_10bar",
            correctness_gate_passed=True,
            passed=True,
            reason="",
            latency_ms=Decimal(10000),  # 10s > 5s max
            event_count=3,
        )
        for i in range(5)
    )
    ev = POCEvidence(
        protocol=POCProtocol(max_latency_ms=Decimal(5000)),
        engine="custom_baseline",
        results=results,
    )
    assert ev.meets_acceptance_criteria() is False


# --- RepresentativeDataset ---


def test_representative_dataset_500_has_500_bars():
    """Canonical 500-bar dataset has exactly 500 bars."""
    ds = RepresentativeDataset.canonical_500()
    assert len(ds.bars) == 500
    assert ds.symbol == "XAUUSD"
    assert ds.timeframe == "M1"


def test_representative_dataset_is_deterministic():
    """Same seed produces identical dataset."""
    ds1 = RepresentativeDataset.canonical_500()
    ds2 = RepresentativeDataset.canonical_500()
    assert ds1.bars == ds2.bars


def test_representative_dataset_has_valid_ohlc():
    """Every bar satisfies low <= min(open, close) <= max(open, close) <= high."""
    ds = RepresentativeDataset.canonical_500()
    for bar in ds.bars:
        ts, o, h, l, c, v = bar
        assert l <= min(o, c) <= max(o, c) <= h, f"invalid OHLC at ts={ts}"
        assert v > 0, f"non-positive volume at ts={ts}"


# --- StressDataset ---


def test_stress_gap_through_stop_has_gap():
    """Stress dataset has a bar that gaps through the stop level."""
    ds = StressDataset.gap_through_stop()
    assert ds.name == "stress_gap_through_stop"
    assert len(ds.bars) == 5
    # Bar 2 gaps through: open=101, high=103, low=99 - gaps through 100 level
    _ts, o, h, l, _c, _v = ds.bars[1]
    assert o == Decimal(101)
    assert h == Decimal(103)
    assert l == Decimal(99)


# --- run_poc_protocol ---


def test_run_protocol_uses_canonical_fixture_by_default():
    """Protocol uses canonical fixture when none specified."""
    ev = run_poc_protocol("custom_baseline")
    assert ev.engine == "custom_baseline"
    assert ev.protocol.name == "standardized_poc_v1"
    assert len(ev.results) == 5  # 5 measured repetitions


def test_run_protocol_all_baseline_runs_pass():
    """All baseline runs pass correctness gate."""
    ev = run_poc_protocol("custom_baseline")
    assert ev.all_passed is True
    assert ev.all_correctness_passed is True


def test_run_protocol_meets_acceptance_for_baseline():
    """Baseline engine meets acceptance criteria."""
    ev = run_poc_protocol("custom_baseline")
    assert ev.meets_acceptance_criteria() is True


def test_run_protocol_unknown_engine_raises():
    """Unknown engine raises error."""
    with pytest.raises(ValueError):  # wrapped from UnknownStrategyRuleError
        run_poc_protocol("nonexistent_engine")


def test_run_protocol_discards_warmup():
    """Warm-up repetition is discarded from results."""
    ev = run_poc_protocol("custom_baseline", protocol=POCProtocol(warm_up_count=1))
    # 5 measured repetitions + 0 additional (no outliers expected)
    assert len(ev.results) == 5
    assert ev.additional_runs_used == 0


def test_run_protocol_has_reproducible_timestamp():
    """Evidence includes a timestamp."""
    ev = run_poc_protocol("custom_baseline")
    assert ev.timestamp_utc > 0


def test_run_protocol_uses_custom_protocol():
    """Custom protocol configuration is honored."""
    protocol = POCProtocol(
        name="test_protocol",
        schema_version="2.0",
        warm_up_count=0,
        measured_repetition_count=3,
        noise_tolerance_pct=Decimal("10.0"),
        max_additional_runs=1,
        min_pass_rate=Decimal("100.0"),
        max_latency_ms=Decimal(10000),
    )
    ev = run_poc_protocol("custom_baseline", protocol=protocol)
    assert ev.protocol.name == "test_protocol"
    assert ev.protocol.schema_version == "2.0"
    assert len(ev.results) == 3


def test_run_protocol_invalid_protocol_raises():
    """Invalid protocol raises ValueError."""
    protocol = POCProtocol(measured_repetition_count=0)  # invalid
    with pytest.raises(ValueError):
        run_poc_protocol("custom_baseline", protocol=protocol)


# --- Deterministic replay ---


def test_run_protocol_deterministic_across_calls():
    """Same engine + protocol produces identical results across calls."""
    ev1 = run_poc_protocol("custom_baseline")
    ev2 = run_poc_protocol("custom_baseline")
    # Results should match (same fixture, same engine, deterministic simulator)
    assert ev1.all_passed == ev2.all_passed
    assert ev1.pass_rate == ev2.pass_rate
    assert ev1.all_correctness_passed == ev2.all_correctness_passed


def test_run_protocol_records_metrics():
    """Evidence results include latency and event count metrics."""
    ev = run_poc_protocol("custom_baseline")
    for r in ev.results:
        assert r.latency_ms >= Decimal(0)
        assert r.event_count > 0
        assert r.first_entry_price is not None
        assert r.first_exit_reason is not None