"""PF/Sharpe/Sortino/DD/trade-count gates with documented conventions (schema.md section 6.3).

Evaluates BaselineMetrics against explicit threshold gates. All thresholds are
explicit numeric parameters with documented conventions; no discretionary terms.
A gate passes only when every threshold is satisfied; any failure blocks.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal


class GateVerdict:
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class GateSpec:
    """Versioned gate specification with explicit Decimal thresholds."""

    schema_version: str
    spec_id: str
    min_pf: Decimal
    min_sharpe: Decimal
    min_sortino: Decimal
    max_dd_pct: Decimal
    min_win_rate_pct: Decimal
    min_trade_count: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "min_pf", Decimal(str(self.min_pf)))
            object.__setattr__(self, "min_sharpe", Decimal(str(self.min_sharpe)))
            object.__setattr__(self, "min_sortino", Decimal(str(self.min_sortino)))
            object.__setattr__(self, "max_dd_pct", Decimal(str(self.max_dd_pct)))
            object.__setattr__(self, "min_win_rate_pct", Decimal(str(self.min_win_rate_pct)))
        except (decimal.InvalidOperation, TypeError) as exc:
            raise ValueError(f"invalid Decimal value in GateSpec: {exc}") from exc
        object.__setattr__(self, "min_trade_count", int(self.min_trade_count))


@dataclass(frozen=True)
class GateResult:
    """Result of evaluating metrics against gate thresholds."""

    spec_id: str
    verdict: str  # GateVerdict.PASS or GateVerdict.FAIL
    failures: list[str]


def evaluate_gates(
    metrics: dict,
    spec: GateSpec,
) -> GateResult:
    """Evaluate baseline metrics against explicit threshold gates.

    Returns GateResult with verdict PASS only when every threshold is met;
    otherwise FAIL with the list of failing gate names.

    Documented conventions:
      - min_pf >= 1.5: profit factor must exceed 1.5 (gross profits exceed gross losses by 50%)
      - min_sharpe >= 1.0: risk-adjusted return per unit of volatility
      - min_sortino >= 1.0: downside-risk-adjusted return
      - max_dd_pct <= 10: maximum drawdown capped at 10%
      - min_win_rate_pct >= 40: win rate at least 40%
      - min_trade_count >= 10: sufficient trade count for statistical significance
    """
    failures = []

    if Decimal(str(metrics.get("pf", 0))) < spec.min_pf:
        failures.append("min_pf")
    if Decimal(str(metrics.get("sharpe", 0))) < spec.min_sharpe:
        failures.append("min_sharpe")
    if Decimal(str(metrics.get("sortino", 0))) < spec.min_sortino:
        failures.append("min_sortino")
    if Decimal(str(metrics.get("max_dd_pct", 0))) > spec.max_dd_pct:
        failures.append("max_dd_pct")
    if Decimal(str(metrics.get("win_rate_pct", 0))) < spec.min_win_rate_pct:
        failures.append("min_win_rate_pct")
    if int(metrics.get("trade_count", 0)) < spec.min_trade_count:
        failures.append("min_trade_count")

    verdict = GateVerdict.PASS if not failures else GateVerdict.FAIL
    return GateResult(spec_id=spec.spec_id, verdict=verdict, failures=list(failures))
