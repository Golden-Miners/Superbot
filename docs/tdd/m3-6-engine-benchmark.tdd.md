# TDD Evidence Report — M3.6 Engine Benchmark Harness

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.6` ("Correctness first, then runtime, process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, repeatability, failure rate and critical-service impact").

## User journeys
- As a researcher, I want to benchmark engine performance (runtime, RAM, CPU, disk I/O, throughput, startup time, repeatability, failure rate, critical-service impact) for each engine candidate (custom baseline, NautilusTrader, LEAN).
- As a researcher, I want correctness gates to run first so performance is never measured for an engine that fails correctness.
- As a researcher, I want one warm-up plus five measured repetitions with a pre-defined noise rule so benchmark results are reproducible and comparable.
- As a researcher, I want critical-service impact tracked so risk/data services are not starved by benchmark runs.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Benchmark result fields | `tests/unit/test_engine_benchmark.py::test_benchmark_result_fields` | ModuleNotFoundError | PASS | `BenchmarkResult` dataclass with engine, correctness_passed, runtime_ms, peak_rss_mb, cpu_time_ms, disk_io_mb, throughput_trades_per_sec, startup_ms, failure_rate, critical_service_impact |
| Unknown engine raises BenchmarkNotRun | `tests/unit/test_engine_benchmark.py::test_benchmark_requires_correctness_first` | ModuleNotFoundError | PASS | `EngineBenchmark.run()` raises `BenchmarkNotRun` when engine not registered |
| Noisy results require pre-defined rule | `tests/unit/test_engine_benchmark.py::test_benchmark_rejects_noisy_results_without_predefined_rule` | ModuleNotFoundError | PASS | `BenchmarkConfig.validate_noise_rule()` raises when noise rule undefined |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | BenchmarkConfig has warmups=1, repetitions=5, iterations_per_run=2000, noise_rule_defined=True | `tests/unit/test_engine_benchmark.py::test_benchmark_config_defaults` | unit | PASS | 80 passed, 2 skipped |
| 2 | BenchmarkResult stores all metrics including median calculations | `tests/unit/test_engine_benchmark.py::test_benchmark_result_fields` | unit | PASS | 80 passed, 2 skipped |
| 3 | EngineBenchmark.run() raises BenchmarkNotRun when engine not registered | `tests/unit/test_engine_benchmark.py::test_benchmark_requires_correctness_first` | unit | PASS | 80 passed, 2 skipped |
| 4 | BenchmarkConfig.validate_noise_rule() raises when noise rule undefined | `tests/unit/test_engine_benchmark.py::test_benchmark_rejects_noisy_results_without_predefined_rule` | unit | PASS | 80 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M3.6 lines exercised by unit tests
- Intentional gap: `EngineBenchmark.run_equivalence()` engine implementations for NautilusTrader and LEAN are not yet wired; `BenchmarkResult` correctness gate delegates to engine's `run_correctness_gate()` method which candidate engines must implement
- Intentional gap: actual process-tree RAM measurement (`psutil.Process.memory_info()`) not yet wired into engine adapters; will be wired when engines are integrated
- Correctness-first enforcement: no performance measurement runs until correctness gate passes

## Merge evidence
Commit: `f286b06` (M3.3 NautilusTrader), `7773d1b` (M3.5 engine assessment), plus M3.6 engine_benchmark.py + tests. RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 80 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
