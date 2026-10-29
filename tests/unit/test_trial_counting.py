"""RED tests for M6.5 — Trial counting, baselines/no-trade comparison and multiple-testing controls.

Tests define:
- TrialCounter: counts trials/experiments run, tracks total trials, completed trials, failed trials
- Baseline comparison: compare strategy results against no-trade baseline (buy-and-hold or flat)
- Multiple-testing correction: Bonferroni correction, Benjamini-Hochberg FDR control
- Multiple testing adjustment: adjust p-values for number of tests performed
- Trial registry: track all trials run, their outcomes, and whether they passed gates
- Version tracking: track strategy versions, how many validations each version has undergone
- Archive rule: after three failed validation attempts, archive the strategy version
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.trial_counting import (
    BaselineComparison,
    MultipleTestingCorrection,
    TrialCounter,
    TrialRegistry,
    VersionArchive,
    compare_to_baseline,
    count_trials,
    evaluate_gates_with_multiple_testing,
    version_archive_check,
)


def test_trial_counter_creates():
    """TrialCounter can be created."""
    counter = TrialCounter()
    assert counter is not None


def test_trial_counter_counts_trials():
    """TrialCounter counts trials added."""
    counter = TrialCounter()
    counter.record_trial("trial_1", "long", Decimal("100.0"), Decimal("0.05"), True)
    counter.record_trial("trial_2", "short", Decimal("100.0"), Decimal("-0.03"), False)
    assert counter.total_trials == 2
    counter2 = TrialCounter()
    counter2.record_trial("trial_3", "long", Decimal("100.0"), Decimal("0.10"), True)
    assert counter2.total_trials == 1


def test_trial_counter_tracks_pass_fail():
    """TrialCounter tracks pass/fail counts."""
    counter = TrialCounter()
    counter.record_trial("trial_1", "long", Decimal("100.0"), Decimal("0.05"), True)
    counter.record_trial("trial_2", "short", Decimal("100.0"), Decimal("-0.03"), False)
    counter.record_trial("trial_3", "long", Decimal("100.0"), Decimal("0.10"), True)
    stats = counter.trial_stats()
    assert stats["total"] == 3
    assert stats["passed"] == 2
    assert stats["failed"] == 1


def test_baseline_comparison_creates():
    """BaselineComparison can be created."""
    bc = BaselineComparison()
    assert bc is not None


def test_baseline_comparison_no_trade_baseline():
    """BaselineComparison compares strategy vs no-trade baseline."""
    bc = BaselineComparison()
    # Strategy: buy at 100, sell at 110 = +10% return
    strategy_pnl = Decimal("10.0")
    # No-trade: hold cash, P&L = 0
    baseline_pnl = Decimal("0.0")
    result = bc.compare(strategy_pnl, baseline_pnl)
    assert result["strategy_pnl"] == Decimal("10.0")
    assert result["baseline_pnl"] == Decimal("0.0")
    assert result["excess_return"] == Decimal("10.0")
    assert result["beat_baseline"] is True


def test_baseline_comparison_worse_than_baseline():
    """Baseline comparison shows when strategy underperforms no-trade."""
    bc = BaselineComparison()
    strategy_pnl = Decimal("-5.0")  # lost money
    baseline_pnl = Decimal("0.0")
    result = bc.compare(strategy_pnl, baseline_pnl)
    assert result["beat_baseline"] is False


def test_evaluate_gates_with_multiple_testing():
    """evaluate_gates_with_multiple_testing applies multiple testing correction."""
    evaluator = MultipleTestingCorrection()
    # 10 trials, 3 passed, 7 failed
    gate_results = [
        ("gate_1", True),
        ("gate_2", False),
        ("gate_3", False),
        ("gate_4", True),
        ("gate_5", False),
        ("gate_6", False),
        ("gate_7", False),
        ("gate_8", False),
        ("gate_9", False),
        ("gate_10", False),
    ]
    result = evaluator.evaluate_with_correction(gate_results, num_tests=10)
    assert result["raw_pass_rate"] == Decimal("0.2")  # 2/10
    assert result["adjusted_pass_rate"] <= Decimal("0.2")  # adjusted should be <= raw


def test_trial_registry_creates():
    """TrialRegistry can be created."""
    registry = TrialRegistry()
    assert registry is not None


def test_trial_registry_registers_trial():
    """TrialRegistry registers trials."""
    registry = TrialRegistry()
    registry.register_trial("trial_1", "long", Decimal("100.0"), Decimal("0.05"))
    assert registry.get_trial("trial_1") is not None


def test_trial_registry_get_nonexistent():
    """TrialRegistry.get_trial returns None for nonexistent trial."""
    registry = TrialRegistry()
    assert registry.get_trial("nonexistent") is None


def test_version_archive_creates():
    """VersionArchive can be created."""
    archive = VersionArchive()
    assert archive is not None


def test_version_archive_after_three_failures():
    """VersionArchive archives version after three failed validations."""
    archive = VersionArchive()
    # Three failed validations for version "v1"
    archive.record_validation("v1", False)
    archive.record_validation("v1", False)
    archive.record_validation("v1", False)
    assert archive.is_archived("v1") is True


def test_version_archive_not_archived_before_three_failures():
    """VersionArchive does not archive before three failures."""
    archive = VersionArchive()
    archive.record_validation("v1", False)
    archive.record_validation("v1", False)
    assert archive.is_archived("v1") is False


def test_count_trials_function():
    """count_trials counts trials."""
    counter = TrialCounter()
    counter.record_trial("t_1", "long", Decimal("100.0"), Decimal("0.05"), True)
    counter.record_trial("t_2", "short", Decimal("100.0"), Decimal("-0.03"), False)
    assert count_trials(counter) == 2


def test_compare_to_baseline_function():
    """compare_to_baseline compares strategy vs baseline."""
    result = compare_to_baseline(Decimal("10.0"), Decimal("0.0"))
    assert result["beat_baseline"] is True
    assert result["excess_return"] == Decimal("10.0")


def test_evaluate_gates_with_multiple_testing_function():
    """evaluate_gates_with_multiple_testing applies multiple testing correction."""
    evaluator = MultipleTestingCorrection()
    gate_results = [
        ("g1", True),
        ("g2", False),
        ("g3", False),
    ]
    result = evaluate_gates_with_multiple_testing(evaluator, gate_results, num_tests=3)
    assert result["raw_pass_rate"] == Decimal("0.3333")  # 1/3 ≈ 0.33


def test_version_archive_check_function():
    """version_archive_check checks if version should be archived."""
    archive = VersionArchive()
    archive.record_validation("v1", False)
    archive.record_validation("v1", False)
    archive.record_validation("v1", False)
    assert version_archive_check(archive, "v1") is True
