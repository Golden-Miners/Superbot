"""Engine performance benchmark harness for M3.6.

Measures runtime, process-tree peak RAM/working set, CPU, disk I/O,
throughput, startup, repeatability, failure rate, and critical-service
impact for engine POC candidates (custom baseline, NautilusTrader, LEAN).

Correctness gate runs first; performance only measured after correctness PASS.
Stdlib-only at import time; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any


class BenchmarkNotRun(RuntimeError):
    """Raised when benchmark result is accessed before running."""


class BenchmarkConfig:
    """Standardized POC protocol benchmark configuration."""

    def __init__(
        self,
        warmups: int = 1,
        repetitions: int = 5,
        iterations_per_run: int = 2000,
        noise_rule_defined: bool = True,
    ) -> None:
        self.warmups = warmups
        self.repetitions = repetitions
        self.iterations_per_run = iterations_per_run
        self.noise_rule_defined = noise_rule_defined

    def validate_noise_rule(self) -> None:
        if not self.noise_rule_defined:
            raise ValueError("noise rule must be defined before reviewing benchmark outcomes")


@dataclass(frozen=True)
class BenchmarkResult:
    """Comparable metrics for one engine candidate."""

    engine: str
    correctness_passed: bool
    runtime_ms: list[float]
    peak_rss_mb: list[float]
    cpu_time_ms: list[float]
    disk_io_mb: list[float]
    throughput_trades_per_sec: list[float]
    startup_ms: float
    failure_rate: float
    critical_service_impact: str

    @property
    def median_runtime_ms(self) -> float:
        return statistics.median(self.runtime_ms)

    @property
    def median_peak_rss_mb(self) -> float:
        return statistics.median(self.peak_rss_mb)

    @property
    def median_throughput_trades_per_sec(self) -> float:
        return statistics.median(self.throughput_trades_per_sec)


class EngineBenchmark:
    """Runs correctness gate first, then performance benchmark for an engine."""

    def __init__(self) -> None:
        self.config = BenchmarkConfig()
        self._engines: dict[str, Any] = {}
        self._results: dict[str, BenchmarkResult] = {}

    def register_engine(self, engine_id: str, engine: Any) -> None:
        self.engines[engine_id] = engine

    def run(self, engine_id: str) -> BenchmarkResult:
        if engine_id in self._results:
            return self._results[engine_id]

        if engine_id not in self._engines:
            raise BenchmarkNotRun(f"engine {engine_id!r} not registered")

        self.config.validate_noise_rule()

        engine = self._engines[engine_id]
        correctness_passed = engine.run_correctness_gate()
        if not correctness_passed:
            result = BenchmarkResult(
                engine=engine_id,
                correctness_passed=False,
                runtime_ms=[],
                peak_rss_mb=[],
                cpu_time_ms=[],
                disk_io_mb=[],
                throughput_trades_per_sec=[],
                startup_ms=0.0,
                failure_rate=1.0,
                critical_service_impact="correctness_failure",
            )
            self._results[engine_id] = result
            return result

        # Warm-up
        for _ in range(self.config.warmups):
            engine.run_bars(self.config.iterations_per_run)

        # Measured repetitions
        runtime_ms = []
        peak_rss_mb = []
        cpu_time_ms = []
        disk_io_mb = []
        throughput_list = []

        for _ in range(self.config.repetitions):
            runtime, peak_rss, cpu, disk_io, throughput = engine.run_benchmark(
                self.config.iterations_per_run
            )
            runtime_ms.append(runtime)
            peak_rss_mb.append(peak_rss)
            cpu_time_ms.append(cpu)
            disk_io_mb.append(disk_io)
            throughput_list.append(throughput)

        startup_ms = engine.measure_startup_ms()
        failure_rate = engine.failure_rate()
        critical_service_impact = engine.critical_service_impact()

        result = BenchmarkResult(
            engine=engine_id,
            correctness_passed=True,
            runtime_ms=runtime_ms,
            peak_rss_mb=peak_rss_mb,
            cpu_time_ms=cpu_time_ms,
            disk_io_mb=disk_io_mb,
            throughput_trades_per_sec=throughput_list,
            startup_ms=startup_ms,
            failure_rate=failure_rate,
            critical_service_impact=critical_service_impact,
        )
        self._results[engine_id] = result
        return result
