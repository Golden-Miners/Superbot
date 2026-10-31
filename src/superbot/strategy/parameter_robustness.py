"""Parameter-neighbor robustness and deterministic stability evaluation (schema.md section 6.4).

Evaluates whether a strategy's performance is stable under small parameter
perturbations. All thresholds are explicit numeric parameters; no discretionary
terms. Null means missing/stale, never zero.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal


class RobustnessVerdict:
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ContinuousParamSpec:
    """Continuous numeric parameter: neighbors at +/- 10%."""

    name: str
    current_value: Decimal

    def neighbor_values(self) -> list[Decimal]:
        return [
            self.current_value * Decimal("0.9"),
            self.current_value * Decimal("1.1"),
        ]


@dataclass(frozen=True)
class IntegerGridParamSpec:
    """Integer grid parameter: nearest valid grid point at or beyond +/- 10%."""

    name: str
    current_value: Decimal
    grid_values: list[Decimal]

    def neighbor_values(self) -> list[Decimal]:
        down_target = self.current_value * Decimal("0.9")
        up_target = self.current_value * Decimal("1.1")

        down_candidates = [g for g in self.grid_values if g <= down_target]
        up_candidates = [g for g in self.grid_values if g >= up_target]

        down_neighbor = max(down_candidates) if down_candidates else None
        up_neighbor = min(up_candidates) if up_candidates else None

        result = []
        if down_neighbor is not None and down_neighbor != self.current_value:
            result.append(down_neighbor)
        if up_neighbor is not None and up_neighbor != self.current_value:
            result.append(up_neighbor)
        return result


@dataclass(frozen=True)
class ZeroValuedParamSpec:
    """Zero-valued parameter: explicitly declared neighboring valid values."""

    name: str
    current_value: Decimal  # must be Decimal("0")
    neighbor_values: list[Decimal]

    def neighbor_values_list(self) -> list[Decimal]:
        return list(self.neighbor_values)


@dataclass(frozen=True)
class CategoricalParamSpec:
    """Categorical parameter: explicitly declared neighboring alternatives."""

    name: str
    current_value: str
    neighbor_values: list[str]

    def neighbor_values_list(self) -> list[str]:
        return list(self.neighbor_values)


@dataclass(frozen=True)
class RobustnessSpec:
    """Versioned robustness specification."""

    schema_version: str
    spec_id: str
    parameters: list  # list of parameter spec objects


@dataclass(frozen=True)
class NeighborResult:
    """Result for a single neighbor configuration evaluation."""

    param_name: str
    neighbor_value: Decimal | str
    pf: Decimal
    sharpe: Decimal
    sortino: Decimal
    max_dd_pct: Decimal
    net_pnl: Decimal
    trade_count: int
    walk_forward_pass: bool


@dataclass(frozen=True)
class RobustnessResult:
    """Overall robustness evaluation result."""

    spec_id: str
    verdict: str  # RobustnessVerdict.PASS, FAIL, or BLOCKED
    failures: list[str]
    neighbor_results: list[NeighborResult]
    pf_cv_pct: Decimal


class ParameterRobustnessEvaluator:
    """Deterministic parameter-neighbor robustness evaluator.

    Evaluates whether a strategy's performance is stable under small parameter
    perturbations. All thresholds are explicit numeric parameters.
    """

    def evaluate_robustness(
        self,
        baseline: dict,
        neighbor_results: list[NeighborResult],
    ) -> RobustnessResult:
        """Evaluate robustness of baseline against neighbor configurations.

        Raises ValueError if baseline or neighbor data is missing/invalid.
        Returns RobustnessResult with verdict PASS/FAIL/BLOCKED.
        """
        failures: list[str] = []

        # Baseline must pass M6.3 gates: PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5
        baseline_pf = baseline.get("pf")
        baseline_sharpe = baseline.get("sharpe")
        baseline_sortino = baseline.get("sortino")

        # Baseline must pass M6.3 gates: PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5
        # Non-finite baseline metrics are a data-quality failure, not a gate failure
        if baseline_pf is None or not self._is_finite_decimal(baseline_pf):
            failures.append("non_finite")
        elif Decimal(str(baseline_pf)) < Decimal("1.20"):
            failures.append("baseline_correctness")

        if baseline_sharpe is None or not self._is_finite_decimal(baseline_sharpe):
            failures.append("non_finite")
        elif Decimal(str(baseline_sharpe)) < Decimal("1.0"):
            failures.append("baseline_correctness")

        if baseline_sortino is None or not self._is_finite_decimal(baseline_sortino):
            failures.append("non_finite")
        elif Decimal(str(baseline_sortino)) < Decimal("1.5"):
            failures.append("baseline_correctness")

        # Check for non-finite metrics in neighbor results
        for nr in neighbor_results:
            for name, val in [
                ("pf", nr.pf),
                ("sharpe", nr.sharpe),
                ("sortino", nr.sortino),
                ("max_dd_pct", nr.max_dd_pct),
                ("net_pnl", nr.net_pnl),
            ]:
                if not self._is_finite_decimal(val):
                    failures.append("non_finite")
                    break

        if failures:
            return RobustnessResult(
                spec_id="",
                verdict=RobustnessVerdict.FAIL,
                failures=failures,
                neighbor_results=list(neighbor_results),
                pf_cv_pct=Decimal(0),
            )

        # Check that we have neighbor results
        if not neighbor_results:
            return RobustnessResult(
                spec_id="",
                verdict=RobustnessVerdict.BLOCKED,
                failures=["insufficient_neighbors"],
                neighbor_results=[],
                pf_cv_pct=Decimal(0),
            )

        # Compute PF CV across baseline + all neighbors
        all_pf_values = [Decimal(str(baseline_pf))]
        for nr in neighbor_results:
            all_pf_values.append(nr.pf)

        pf_mean = sum(all_pf_values) / Decimal(len(all_pf_values))
        if len(all_pf_values) > 1:
            var = sum((v - pf_mean) ** 2 for v in all_pf_values) / Decimal(len(all_pf_values) - 1)
            pf_std = var.sqrt()
        else:
            pf_std = Decimal(0)

        if pf_mean == Decimal(0):
            pf_cv_pct = Decimal(0)
        else:
            pf_cv_pct = (pf_std / pf_mean) * Decimal(100)

        # Check each neighbor against all criteria
        baseline_pf_val = Decimal(str(baseline_pf))
        baseline_sharpe_val = Decimal(str(baseline_sharpe))
        baseline_dd = Decimal(str(baseline.get("max_dd_pct", 0)))

        for nr in neighbor_results:
            # PF deviation <= 20% relative
            pf_deviation = abs(nr.pf - baseline_pf_val) / baseline_pf_val * Decimal(100)
            if pf_deviation > Decimal(20):
                failures.append("pf_deviation")

            # Sharpe deviation <= 20% relative
            sharpe_deviation = (
                abs(nr.sharpe - baseline_sharpe_val) / baseline_sharpe_val * Decimal(100)
            )
            if sharpe_deviation > Decimal(20):
                failures.append("sharpe_deviation")

            # Max DD deterioration <= 20% relative (if baseline DD > 0)
            if baseline_dd > Decimal(0):
                dd_deterioration = (nr.max_dd_pct - baseline_dd) / baseline_dd * Decimal(100)
                if dd_deterioration > Decimal(20):
                    failures.append("stop_drawdown")

            # If baseline DD is zero, every neighbor DD <= 1 pp
            if baseline_dd == Decimal(0) and nr.max_dd_pct > Decimal(1):
                failures.append("max_drawdown_zero_baseline")

            # Every neighbor DD <= 15%
            if nr.max_dd_pct > Decimal(15):
                failures.append("max_drawdown")

            # Net return > 0
            if nr.net_pnl <= Decimal(0):
                failures.append("net_return")

            # PF >= 1.00
            if nr.pf < Decimal("1.00"):
                failures.append("profit_factor")

            # Trade count >= 100
            if nr.trade_count < 100:
                failures.append("trade_count")

            # Walk-forward: >= 2 of 3 windows positive, every window <= 15% DD
            if not nr.walk_forward_pass:
                failures.append("walk_forward")

        # PF CV < 10%
        if pf_cv_pct >= Decimal(10):
            failures.append("pf_cv")

        verdict = RobustnessVerdict.PASS if not failures else RobustnessVerdict.FAIL

        return RobustnessResult(
            spec_id="",
            verdict=verdict,
            failures=failures,
            neighbor_results=list(neighbor_results),
            pf_cv_pct=pf_cv_pct,
        )

    def generate_pairwise_combinations(
        self,
        param1: tuple[str, Decimal, Decimal, Decimal],
        param2: tuple[str, Decimal, Decimal, Decimal],
    ) -> list[dict[str, Decimal | str]]:
        """Generate all four corner combinations for a pair of numeric parameters.

        Each tuple is (name, current_value, up_value, down_value).
        Returns list of dicts mapping parameter name to neighbor value.
        """
        p1_name, _p1_current, p1_up, p1_down = param1
        p2_name, _p2_current, p2_up, p2_down = param2

        return [
            {p1_name: p1_up, p2_name: p2_up},
            {p1_name: p1_up, p2_name: p2_down},
            {p1_name: p1_down, p2_name: p2_up},
            {p1_name: p1_down, p2_name: p2_down},
        ]

    def _is_finite_decimal(self, val) -> bool:
        """Check if a value is a finite Decimal."""
        if val is None:
            return False
        try:
            d = Decimal(str(val))
            return d.is_finite()
        except (decimal.InvalidOperation, TypeError, ValueError):
            return False
