"""RED tests for M3.6 — Engine performance benchmark.

Tests define:
- Benchmark harness measures runtime, process-tree peak RAM, CPU, disk I/O,
  throughput, startup, repeatability for each engine candidate.
- Correctness gate runs first; performance only measured after correctness PASS.
- One warm-up + five measured repetitions standard.
- Repetition noise rule defined before viewing results.
- Critical-service impact checked (risk/data services not starved).
"""

from __future__ import annotations

import pytest

from superbot.engine.engine_benchmark import (
    BenchmarkConfig,
    BenchmarkNotRun,
    BenchmarkResult,
    EngineBenchmark,
)


def test_benchmark_config_defaults():
    """Benchmark config uses standardized POC protocol defaults."""
    config = BenchmarkConfig()
    assert config.warmups == 1
    assert config.repetitions == 5
    assert config.iterations_per_run == 2000
    assert config.noise_rule_defined is True


def test_benchmark_result_fields():
    """Benchmark result captures all required metrics."""
    result = BenchmarkResult(
        engine="custom_baseline",
        correctness_passed=True,
        runtime_ms=[25.0, 26.0, 24.5, 27.0, 25.5],
        peak_rss_mb=[30.0, 31.0, 29.5, 30.5, 30.2],
        cpu_time_ms=[5.0, 5.2, 4.8, 5.1, 5.3],
        disk_io_mb=[0.5, 0.6, 0.4, 0.5, 0.5],
        throughput_trades_per_sec=[1000.0, 1050.0, 980.0, 1020.0, 1010.0],
        startup_ms=1500.0,
        failure_rate=0.0,
        critical_service_impact="none",
    )
    assert result.engine == "custom_baseline"
    assert result.correctness_passed is True
    assert len(result.runtime_ms) == 5
    assert result.median_runtime_ms == 25.5


def test_benchmark_requires_correctness_first():
    """Benchmark cannot run without correctness gate passing."""
    engine = EngineBenchmark()
    with pytest.raises(BenchmarkNotRun):
        engine.run("custom_baseline")


def test_benchmark_rejects_noisy_results_without_predefined_rule():
    """Noisy results require pre-defined noise rule before acceptance."""
    config = BenchmarkConfig()
    config.noise_rule_defined = False
    with pytest.raises(ValueError):
        config.validate_noise_rule()
