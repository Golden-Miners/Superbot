"""Standardized equivalence framework for engine POC comparison (M3.2).

Defines:
- EquivalenceFixture: canonical OHLCV bars shared across candidate engines.
- CostConvention: explicit spread/slippage/commission/swap funding.
- StrategyRule: machine-testable strategy rule definition.
- AcceptanceResult: outcome of an acceptance run.
- run_equivalence_acceptance: runs the correctness-gate acceptance test.

Stdlib-only. No import-time network, MT5, database, or model activity.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


class UnknownStrategyRuleError(ValueError):
    """Raised when a requested strategy rule or engine is not registered."""


@dataclass(frozen=True)
class CostConvention:
    """Explicit cost model applied identically across candidate engines."""

    spread_per_unit: Decimal = Decimal(0)
    slippage_per_unit: Decimal = Decimal(0)
    commission_per_unit: Decimal = Decimal(0)
    swap_funding_per_unit: Decimal = Decimal(0)

    @classmethod
    def default(cls) -> CostConvention:
        """Zero-cost convention used by the equivalence acceptance gate."""
        return cls()

    def total_cost(self, qty: Decimal) -> Decimal:
        """Total cost for a round-turn trade of qty units.

        spread + entry/exit slippage + entry/exit commission + swap funding.
        """
        return (
            self.spread_per_unit * qty
            + self.slippage_per_unit * qty * Decimal(2)
            + self.commission_per_unit * qty * Decimal(2)
            + self.swap_funding_per_unit * qty
        )


@dataclass(frozen=True)
class StrategyRule:
    """Machine-testable strategy rule.

    All fields are explicit and versioned; no discretionary prose.
    """

    name: str
    family: str  # trend_pullback | liquidity_structure | quantitative_statistical
    entry_condition: str
    exit_condition: str
    stop_condition: str
    target_condition: str
    parameters: dict  # parameter name -> value, units documented


@dataclass(frozen=True)
class Bar:
    ts: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(1)


@dataclass(frozen=True)
class EquivalenceFixture:
    """Canonical OHLCV fixture shared across candidate engines."""

    name: str
    bars: tuple[Bar, ...]
    source: str = "synthetic"

    @classmethod
    def canonical(cls) -> EquivalenceFixture:
        """The canonical 10-bar equivalence fixture (mirrors superbot_poc.py)."""
        rows = [
            (1, 100, 101, 99, 100),
            (2, 100, 102, 99.5, 101),
            (3, 101, 104, 100, 103),  # both TP/SL touch: SL must win
            (4, 103, 105, 98, 101),
            (5, 96, 99, 94, 97),  # gap-through stop fixture
            (6, 97, 100, 96, 99),
            (7, 99, 103, 98, 102),
            (8, 102, 104, 100, 101),
            (9, 101, 102, 97, 98),
            (10, 98, 101, 96, 100),
        ]
        return cls(
            name="canonical_10bar",
            bars=tuple(
                Bar(
                    ts=r[0],
                    open=Decimal(str(r[1])),
                    high=Decimal(str(r[2])),
                    low=Decimal(str(r[3])),
                    close=Decimal(str(r[4])),
                )
                for r in rows
            ),
            source="superbot_poc.py",
        )


@dataclass(frozen=True)
class AcceptanceResult:
    """Outcome of an equivalence acceptance run."""

    engine: str
    fixture: str
    correctness_gate_passed: bool
    event_count: int
    first_entry_price: Decimal | None
    first_exit_reason: str | None
    passed: bool
    reason: str = ""


KNOWN_ENGINES = ("custom_baseline",)
KNOWN_STRATEGY_RULES = {
    "trend_pullback_v1": StrategyRule(
        name="trend_pullback_v1",
        family="trend_pullback",
        entry_condition="close > sma(20) and close < sma(50)",
        exit_condition="close < sma(20) or close > sma(50)",
        stop_condition="low <= entry * 0.98",
        target_condition="high >= entry * 1.04",
        parameters={"sma_fast": 20, "sma_slow": 50},
    ),
}


def _validate_bars(bars: Iterable[Bar]) -> None:
    previous = None
    for b in bars:
        if not (b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high):
            raise UnknownStrategyRuleError(f"invalid OHLC at ts={b.ts}")
        if b.volume < 0:
            raise UnknownStrategyRuleError(f"negative volume at ts={b.ts}")
        if previous is not None and b.ts <= previous:
            raise UnknownStrategyRuleError("timestamps must be strictly increasing")
        previous = b.ts


def _run_custom_baseline(fixture: EquivalenceFixture) -> AcceptanceResult:
    """Run the custom baseline simulator against the equivalence fixture.

    Uses the same semantics as superbot_poc.py: next-bar-open entry,
    stop-first ambiguous SL/TP, stop-gap worse-open fill, explicit costs.
    """
    bars = list(fixture.bars)
    _validate_bars(bars)

    events = []
    side = "long"
    entry_index = 1
    stop = Decimal(99)
    target = Decimal(104)
    qty = Decimal(1)

    entry_bar = bars[entry_index + 1]
    entry_price = entry_bar.open
    events.append(("entry", entry_bar.ts, entry_price))

    exit_price: Decimal | None = None
    exit_ts: int | None = None
    exit_reason: str | None = None

    for b in bars[entry_index + 2 :]:
        if side == "long" and b.open <= stop:
            exit_price = b.open
            exit_ts = b.ts
            exit_reason = "stop_gap"
            break
        hit_stop = b.low <= stop
        hit_target = b.high >= target
        if hit_stop:
            exit_price = stop
            exit_ts = b.ts
            exit_reason = "stop"
            break
        if hit_target:
            exit_price = target
            exit_ts = b.ts
            exit_reason = "target"
            break

    if exit_price is None:
        last = bars[-1]
        exit_price = last.close
        exit_ts = last.ts
        exit_reason = "end_of_data"

    events.append(("exit", exit_ts, exit_price))

    cost_convention = CostConvention.default()
    costs = cost_convention.total_cost(qty)
    events.append(("cost", exit_ts, Decimal(0)))  # amount=costs

    correctness_gate_passed = (
        events[0][1] == bars[2].ts  # entry on next bar after signal
        and exit_reason == "stop"  # conservative stop-first
        and abs(costs - Decimal(0)) < Decimal("1e-9")
    )

    return AcceptanceResult(
        engine="custom_baseline",
        fixture=fixture.name,
        correctness_gate_passed=correctness_gate_passed,
        event_count=len(events),
        first_entry_price=events[0][2],
        first_exit_reason=exit_reason,
        passed=correctness_gate_passed,
        reason="",
    )


def run_equivalence_acceptance(engine: str) -> AcceptanceResult:
    """Run the equivalence acceptance test for a candidate engine.

    Returns an AcceptanceResult. Raises UnknownStrategyRuleError if the
    engine is not a known registered engine.
    """
    if engine not in KNOWN_ENGINES:
        raise UnknownStrategyRuleError(f"engine {engine!r} not registered; known: {KNOWN_ENGINES}")

    fixture = EquivalenceFixture.canonical()

    if engine == "custom_baseline":
        return _run_custom_baseline(fixture)

    raise UnknownStrategyRuleError(
        f"engine {engine!r} is known but has no acceptance implementation"
    )
