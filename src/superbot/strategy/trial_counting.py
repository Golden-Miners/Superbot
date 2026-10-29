"""Trial counting, baselines/no-trade comparison and multiple-testing controls (schema.md section 6.5).

Tracks trial counts, compares strategy results against no-trade baselines, and
applies multiple-testing corrections (Bonferroni correction).
Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TrialResult:
    """Result of a single trial/experiment."""

    trial_id: str
    side: str  # "long" or "short"
    entry_price: Decimal
    pnl: Decimal  # profit/loss
    passed: bool  # did this trial pass its validation gate


class BaselineComparison:
    """Result of comparing strategy results against baseline."""

    def __init__(
        self,
        strategy_pnl: Decimal = Decimal(0),
        baseline_pnl: Decimal = Decimal(0),
        excess_return: Decimal = Decimal(0),
        beat_baseline: bool = False,
    ) -> None:
        self.strategy_pnl = strategy_pnl
        self.baseline_pnl = baseline_pnl
        self.excess_return = excess_return
        self.beat_baseline = beat_baseline

    def __getitem__(self, key: str):
        return getattr(self, key)

    def compare(
        self,
        strategy_pnl: Decimal,
        baseline_pnl: Decimal,
    ) -> BaselineComparison:
        """Compare strategy P&L to baseline P&L."""
        excess = strategy_pnl - baseline_pnl
        return BaselineComparison(
            strategy_pnl=strategy_pnl,
            baseline_pnl=baseline_pnl,
            excess_return=excess,
            beat_baseline=excess > Decimal(0),
        )


class MultipleTestingCorrection:
    """Multiple-testing correction for multiple hypothesis tests.

    Applies Bonferroni correction: adjusted p-value = min(1, raw_p * num_tests).
    For pass rate: adjusted_pass_rate = raw_pass_rate * num_tests / total_tests.
    """

    def __init__(
        self,
        raw_pass_rate: Decimal = Decimal(0),
        adjusted_pass_rate: Decimal = Decimal(0),
        num_tests: int = 0,
        num_passed: int = 0,
    ) -> None:
        self.raw_pass_rate = raw_pass_rate
        self.adjusted_pass_rate = adjusted_pass_rate
        self.num_tests = num_tests
        self.num_passed = num_passed

    def evaluate_with_correction(
        self,
        results: list[tuple[str, bool]],
        num_tests: int,
    ) -> MultipleTestingCorrection:
        """Evaluate multiple test results with correction.

        Args:
            results: list of (test_id, passed) tuples
            num_tests: total number of tests performed (for correction denominator)

        Returns MultipleTestingCorrection with raw_pass_rate, adjusted_pass_rate,
        num_tests, num_passed.
        """
        total = len(results)
        passed = sum(1 for _, p in results if p)
        raw_rate = Decimal(passed) / Decimal(total) if total > 0 else Decimal(0)

        # Bonferroni correction: adjusted = raw_pass_rate * num_tests / total
        # More tests = harder to pass (more conservative)
        if total > 0:
            adjusted = raw_rate * Decimal(num_tests) / Decimal(total)
        else:
            adjusted = Decimal(0)

        # Cap at 1.0
        adjusted = min(adjusted, Decimal(1))

        # Round to 4 decimal places
        raw_rate = raw_rate.quantize(Decimal("0.0001"))
        adjusted = adjusted.quantize(Decimal("0.0001"))

        return MultipleTestingCorrection(
            raw_pass_rate=raw_rate,
            adjusted_pass_rate=adjusted,
            num_tests=num_tests,
            num_passed=passed,
        )

    def __getitem__(self, key: str):
        return getattr(self, key)


class TrialCounter:
    """Counts trials/experiments and tracks pass/fail counts."""

    def __init__(self) -> None:
        self._trials: dict[str, TrialResult] = {}

    def record_trial(
        self,
        trial_id: str,
        side: str,
        entry_price: Decimal,
        pnl: Decimal,
        passed: bool,
    ) -> None:
        """Record a trial result."""
        self._trials[trial_id] = TrialResult(
            trial_id=trial_id,
            side=side,
            entry_price=entry_price,
            pnl=pnl,
            passed=passed,
        )

    @property
    def total_trials(self) -> int:
        """Total number of trials recorded."""
        return len(self._trials)

    @property
    def passed_trials(self) -> int:
        """Number of trials that passed."""
        return sum(1 for t in self._trials.values() if t.passed)

    @property
    def failed_trials(self) -> int:
        """Number of trials that failed."""
        return self.total_trials - self.passed_trials

    def trial_stats(self) -> dict[str, int]:
        """Return trial statistics."""
        return {
            "total": self.total_trials,
            "passed": self.passed_trials,
            "failed": self.failed_trials,
        }


class TrialRegistry:
    """Registry of all trial registrations."""

    def __init__(self) -> None:
        self._trials: dict[str, dict] = {}

    def register_trial(
        self,
        trial_id: str,
        side: str,
        entry_price: Decimal,
        pnl: Decimal,
    ) -> None:
        """Register a trial."""
        self._trials[trial_id] = {
            "trial_id": trial_id,
            "side": side,
            "entry_price": entry_price,
            "pnl": pnl,
        }

    def get_trial(self, trial_id: str) -> dict | None:
        """Retrieve a trial by ID."""
        return self._trials.get(trial_id)


@dataclass(frozen=True)
class VersionArchive:
    """Tracks version validations and archives after 3 failures."""

    version_id: str = ""
    failures: int = 0
    archived: bool = False

    def record_validation(self, version_id: str, passed: bool) -> VersionArchive:
        """Record a validation result. Returns self for chaining."""
        if self.archived:
            return self
        if not passed:
            object.__setattr__(self, "failures", self.failures + 1)
            if self.failures >= 3:
                object.__setattr__(self, "archived", True)
        return self

    def is_archived(self, version_id: str = "") -> bool:
        """Check if a version has been archived."""
        return self.archived


class VersionArchiveManager:
    """Manages version archives across multiple versions."""

    def __init__(self) -> None:
        self._archives: dict[str, VersionArchive] = {}

    def get_archive(self, version_id: str) -> VersionArchive:
        """Get or create an archive for a version."""
        if version_id not in self._archives:
            self._archives[version_id] = VersionArchive(
                version_id=version_id,
                failures=0,
                archived=False,
            )
        return self._archives[version_id]


def count_trials(counter: TrialCounter) -> int:
    """Count total trials in a TrialCounter."""
    return counter.total_trials


def compare_to_baseline(strategy_pnl: Decimal, baseline_pnl: Decimal) -> BaselineComparison:
    """Compare strategy P&L to baseline P&L.

    Returns BaselineComparison with strategy_pnl, baseline_pnl, excess_return
    (strategy - baseline), and beat_baseline flag.
    """
    excess = strategy_pnl - baseline_pnl
    return BaselineComparison(
        strategy_pnl=strategy_pnl,
        baseline_pnl=baseline_pnl,
        excess_return=excess,
        beat_baseline=excess > Decimal(0),
    )


def record_trial(
    counter: TrialCounter,
    trial_id: str,
    side: str,
    entry_price: Decimal,
    pnl: Decimal,
    passed: bool,
) -> None:
    """Record a trial in a TrialCounter."""
    counter.record_trial(trial_id, side, entry_price, pnl, passed)


class MultipleTestingCorrectionEngine:
    """Multiple-testing correction for multiple hypothesis tests.

    Applies Bonferroni correction: adjusted p-value = min(1, raw_p * num_tests).
    For pass rate: adjusted_pass_rate = raw_pass_rate * num_tests / total_tests.
    """

    def evaluate_with_correction(
        self,
        results: list[tuple[str, bool]],
        num_tests: int,
    ) -> MultipleTestingCorrection:
        """Evaluate multiple test results with correction.

        Args:
            results: list of (test_id, passed) tuples
            num_tests: total number of tests performed (for correction denominator)

        Returns MultipleTestingCorrection with raw_pass_rate, adjusted_pass_rate,
        num_tests, num_passed.
        """
        total = len(results)
        passed = sum(1 for _, p in results if p)
        raw_rate = Decimal(passed) / Decimal(total) if total > 0 else Decimal(0)

        # Bonferroni correction: adjusted = raw_pass_rate * num_tests / total
        # More tests = harder to pass (more conservative)
        if total > 0:
            adjusted = raw_rate * Decimal(num_tests) / Decimal(total)
        else:
            adjusted = Decimal(0)

        # Cap at 1.0
        adjusted = min(adjusted, Decimal(1))

        # Round to 4 decimal places
        raw_rate = raw_rate.quantize(Decimal("0.0001"))
        adjusted = adjusted.quantize(Decimal("0.0001"))

        return MultipleTestingCorrection(
            raw_pass_rate=raw_rate,
            adjusted_pass_rate=adjusted,
            num_tests=num_tests,
            num_passed=passed,
        )


def evaluate_gates_with_multiple_testing(
    evaluator: MultipleTestingCorrectionEngine,
    gate_results: list[tuple[str, bool]],
    num_tests: int,
) -> MultipleTestingCorrection:
    """Evaluate gate results with multiple testing correction."""
    return evaluator.evaluate_with_correction(gate_results, num_tests)


def version_archive_check(archive: VersionArchive, version_id: str) -> bool:
    """Check if a version has been archived."""
    return archive.is_archived(version_id)
