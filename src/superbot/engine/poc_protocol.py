"""Standardized POC protocol for engine candidate comparison (M3.7a).

Defines:
- POCProtocol: protocol configuration (correctness gate, warm-up, repetitions,
  noise/additional-run rule, metrics)
- POCRunResult: result of a single POC run
- POCEvidence: reproducible evidence retention across repetitions
- RepresentativeDataset: larger synthetic dataset for performance testing
- StressDataset: optional stress set for boundary conditions
- run_poc_protocol(): executes one warm-up + five measured repetitions,
  applies the strict correctness gate, returns aggregated evidence

Stdlib-only. No import-time network, MT5, database, or model activity.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from statistics import mean

from superbot.engine.equivalence import (
    AcceptanceResult,
    CostConvention,
    EquivalenceFixture,
    StrategyRule,
    run_equivalence_acceptance,
)


@dataclass(frozen=True)
class POCProtocol:
    """Standardized POC protocol configuration.

    All fields are explicit and versioned. No discretionary prose.
    """

    name: str = "standardized_poc_v1"
    schema_version: str = "1.0"

    # Correctness gate: an engine must pass correctness on ALL repetitions
    correctness_required_on_all_repetitions: bool = True

    # Warm-up: one repetition discarded before measurement
    warm_up_count: int = 1

    # Measured repetitions: five measured runs
    measured_repetition_count: int = 5

    # Noise rule: if any repetition deviates from median by > tolerance,
    # one additional run is permitted (max two additional runs total)
    noise_tolerance_pct: Decimal = Decimal("5.0")
    max_additional_runs: int = 2

    # Acceptance thresholds
    min_pass_rate: Decimal = Decimal("100.0")  # 100% required
    max_latency_ms: Decimal = Decimal(5000)  # 5s per run max

    def is_valid(self) -> bool:
        """Validate protocol configuration."""
        return (
            self.warm_up_count >= 0
            and self.measured_repetition_count >= 1
            and self.noise_tolerance_pct >= Decimal(0)
            and self.max_additional_runs >= 0
            and self.min_pass_rate > Decimal(0)
            and self.min_pass_rate <= Decimal(100)
        )


@dataclass(frozen=True)
class POCRunResult:
    """Result of a single POC run."""

    repetition: int
    engine: str
    fixture: str
    correctness_gate_passed: bool
    passed: bool
    reason: str
    latency_ms: Decimal
    event_count: int
    first_entry_price: Decimal | None = None
    first_exit_reason: str | None = None
    cost_convention: CostConvention | None = None
    strategy_rule: StrategyRule | None = None
    metrics: dict[str, Decimal] | None = None

    def is_outlier(self, baseline_latency_ms: Decimal, tolerance_pct: Decimal) -> bool:
        """Return True if this run's latency deviates from baseline by > tolerance."""
        if baseline_latency_ms <= Decimal(0):
            return False
        deviation_pct = abs(self.latency_ms - baseline_latency_ms) / baseline_latency_ms * Decimal(100)
        return deviation_pct > tolerance_pct


@dataclass(frozen=True)
class POCEvidence:
    """Reproducible evidence retention across POC repetitions.

    Stores all run results plus aggregated metrics so benchmark outcomes
    are fully reproducible and auditable.
    """

    protocol: POCProtocol
    engine: str
    results: tuple[POCRunResult, ...]
    additional_runs_used: int = 0
    timestamp_utc: int = 0

    @property
    def all_correctness_passed(self) -> bool:
        """Return True if correctness gate passed on every measured run."""
        return all(r.correctness_gate_passed for r in self.results)

    @property
    def all_passed(self) -> bool:
        """Return True if every measured run passed."""
        return all(r.passed for r in self.results)

    @property
    def pass_rate(self) -> Decimal:
        """Return pass rate as percentage (0-100)."""
        if not self.results:
            return Decimal(0)
        passed = sum(1 for r in self.results if r.passed)
        return Decimal(passed) / Decimal(len(self.results)) * Decimal(100)

    @property
    def median_latency_ms(self) -> Decimal:
        """Return median latency across measured runs."""
        if not self.results:
            return Decimal(0)
        latencies = sorted(r.latency_ms for r in self.results)
        n = len(latencies)
        mid = n // 2
        if n % 2 == 0:
            return (latencies[mid - 1] + latencies[mid]) / Decimal(2)
        return latencies[mid]

    @property
    def mean_latency_ms(self) -> Decimal:
        """Return mean latency across measured runs."""
        if not self.results:
            return Decimal(0)
        return mean([r.latency_ms for r in self.results])

    @property
    def min_latency_ms(self) -> Decimal:
        """Return minimum latency."""
        if not self.results:
            return Decimal(0)
        return min(r.latency_ms for r in self.results)

    @property
    def max_latency_ms(self) -> Decimal:
        """Return maximum latency."""
        if not self.results:
            return Decimal(0)
        return max(r.latency_ms for r in self.results)

    @property
    def mean_event_count(self) -> Decimal:
        """Return mean event count across runs."""
        if not self.results:
            return Decimal(0)
        return mean([Decimal(r.event_count) for r in self.results])

    def meets_acceptance_criteria(self) -> bool:
        """Return True if evidence meets all acceptance criteria."""
        if not self.all_passed:
            return False
        if self.pass_rate < self.protocol.min_pass_rate:
            return False
        if self.median_latency_ms > self.protocol.max_latency_ms:
            return False
        if self.protocol.correctness_required_on_all_repetitions and not self.all_correctness_passed:
            return False
        return not self.additional_runs_used > self.protocol.max_additional_runs


@dataclass(frozen=True)
class RepresentativeDataset:
    """Larger synthetic dataset for performance testing across engines."""

    name: str
    bars: tuple  # tuple of (ts, open, high, low, close, volume)
    source: str = "synthetic"
    symbol: str = "XAUUSD"
    timeframe: str = "M1"

    @classmethod
    def canonical_500(cls) -> RepresentativeDataset:
        """Generate a canonical 500-bar representative dataset.

        Uses a deterministic pseudo-random walk so results are reproducible
        without external data sources.
        """
        import random

        rng = random.Random(42)  # fixed seed for reproducibility
        ts = 1_700_000_000
        price = Decimal("2000.00")
        bars: list = []
        for i in range(500):
            change = Decimal(str(rng.uniform(-5, 5)))
            o = price
            h = o + abs(change) + Decimal(str(rng.uniform(0, 2)))
            l = o - abs(change) - Decimal(str(rng.uniform(0, 2)))
            c = o + change
            c = min(c, h)
            c = max(c, l)
            v = Decimal(str(rng.randint(100, 10000)))
            bars.append((ts + i * 60, o, h, l, c, v))
            price = c
        return cls(
            name="representative_500bar",
            bars=tuple(bars),
            source="deterministic_prng_seed_42",
            symbol="XAUUSD",
            timeframe="M1",
        )


@dataclass(frozen=True)
class StressDataset:
    """Optional stress set for boundary conditions."""

    name: str
    bars: tuple  # tuple of (ts, open, high, low, close, volume)
    source: str = "synthetic"

    @classmethod
    def gap_through_stop(cls) -> StressDataset:
        """Dataset where price gaps through stop loss in a single bar."""
        rows = [
            (1, 100, 102, 98, 101),   # gap up
            (2, 101, 103, 99, 102),   # gap through stop
            (3, 102, 104, 100, 103),
            (4, 103, 105, 101, 104),
            (5, 104, 106, 102, 105),
        ]
        return cls(
            name="stress_gap_through_stop",
            bars=tuple(
                (r[0], Decimal(str(r[1])), Decimal(str(r[2])),
                 Decimal(str(r[3])), Decimal(str(r[4])), Decimal(100))
                for r in rows
            ),
            source="stress_boundary",
        )


def run_poc_protocol(
    engine: str,
    protocol: POCProtocol | None = None,
    fixture: EquivalenceFixture | None = None,
    run_fn: Callable[[str, EquivalenceFixture], AcceptanceResult] = lambda eng, _fix: run_equivalence_acceptance(eng),
) -> POCEvidence:
    """Execute the standardized POC protocol for a candidate engine.

    Runs one warm-up repetition (discarded) + five measured repetitions.
    Applies the strict correctness gate on all measured repetitions.
    If any measured run deviates from median latency by > noise_tolerance_pct,
    permits up to max_additional_runs additional runs.

    Args:
        engine: Engine name (e.g., "custom_baseline").
        protocol: Protocol configuration (defaults to standardized_poc_v1).
        fixture: Equivalence fixture (defaults to canonical 10-bar).
        run_fn: Function that runs a single acceptance test (default:
            run_equivalence_acceptance from equivalence module).

    Returns:
        POCEvidence with all run results and aggregated metrics.

    Raises:
        ValueError: If protocol is invalid.
    """
    protocol = protocol or POCProtocol()
    if not protocol.is_valid():
        raise ValueError("invalid POC protocol configuration")
    fixture = fixture or EquivalenceFixture.canonical()

    results: list[POCRunResult] = []

    # Warm-up repetition(s) - discarded
    for warm in range(protocol.warm_up_count):
        run_fn(engine, fixture)

    # Measured repetitions
    for rep in range(1, protocol.measured_repetition_count + 1):
        import time

        start = time.perf_counter()
        result = run_fn(engine, fixture)
        elapsed_ms = Decimal(str((time.perf_counter() - start) * 1000))

        poc_result = POCRunResult(
            repetition=rep,
            engine=engine,
            fixture=fixture.name,
            correctness_gate_passed=result.correctness_gate_passed,
            passed=result.passed,
            reason=result.reason,
            latency_ms=elapsed_ms,
            event_count=result.event_count,
            first_entry_price=result.first_entry_price,
            first_exit_reason=result.first_exit_reason,
        )
        results.append(poc_result)

    # Noise rule: check for outlier latencies, permit additional runs
    additional_runs_used = 0
    if protocol.max_additional_runs > 0 and results:
        median_lat = POCEvidence(
            protocol=protocol, engine=engine, results=tuple(results),
        ).median_latency_ms
        for rep in range(protocol.measured_repetition_count + 1,
                         protocol.measured_repetition_count + 1 + protocol.max_additional_runs):
            run = results[rep - protocol.measured_repetition_count - 1] if rep <= len(results) else None
            # Check most recent run against median
            if run and run.is_outlier(median_lat, protocol.noise_tolerance_pct):
                import time

                start = time.perf_counter()
                extra_result = run_fn(engine, fixture)
                elapsed_ms = Decimal(str((time.perf_counter() - start) * 1000))
                extra = POCRunResult(
                    repetition=rep,
                    engine=engine,
                    fixture=fixture.name,
                    correctness_gate_passed=extra_result.correctness_gate_passed,
                    passed=extra_result.passed,
                    reason=extra_result.reason,
                    latency_ms=elapsed_ms,
                    event_count=extra_result.event_count,
                    first_entry_price=extra_result.first_entry_price,
                    first_exit_reason=extra_result.first_exit_reason,
                )
                results.append(extra)
                additional_runs_used += 1

    import time as _time

    return POCEvidence(
        protocol=protocol,
        engine=engine,
        results=tuple(results),
        additional_runs_used=additional_runs_used,
        timestamp_utc=int(_time.time()),
    )