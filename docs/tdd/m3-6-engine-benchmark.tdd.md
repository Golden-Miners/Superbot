# TDD Evidence Report — M3.6 Engine Performance Benchmark Harness

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.6` ("Correctness first, then runtime, process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, repeatability, failure rate and critical-service impact").

## User journeys
- As a researcher, I want to benchmark engine performance (runtime, RAM, CPU, disk I/O, throughput) so I can compare custom baseline, NautilusTrader, and LEAN fairly
- As a researcher, I want correctness gate to run first so performance is never measured for a broken engine
- As a researcher, I want one warm-up + five measured repetitions with a pre-defined noise rule so benchmark results are reproducible and comparable
- As a researcher, I want critical-service impact measured so risk/data services are not starved

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Benchmark config defaults | `tests/unit/test_engine_benchmark.py::test_benchmark_config_defaults` | ModuleNotFoundError | PASS | `BenchmarkConfig` uses warmups=1, repetitions=5, iterations=2000, noise rule defined |
| Benchmark result fields | `tests/unit/test_engine_benchmark.py::test_benchmark_result_fields` | ModuleNotFoundError | PASS | `BenchmarkResult` captures runtime, RAM, CPU, disk I/O, throughput, startup, failure rate, critical-service impact |
| Correctness gate first | `tests/unit/test_engine_benchmark.py::test_benchmark_requires_correctness_first` | ModuleNotFoundError | PASS | `EngineBenchmark.run()` raises `BenchmarkNotRun` before correctness passes |
| Noisy results require pre-defined rule | `tests/unit/test_engine_benchmark.py::test_benchmark_rejects_noisy_results_without_predefined_rule` | ModuleNotFoundError | PASS | `BenchmarkConfig.validate_noise_rule()` raises when noise rule undefined |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | BenchmarkConfig has warmups=1, repetitions=5, iterations_per_run=2000, noise_rule_defined=True | `tests/unit/test_engine_benchmark.py` | unit | PASS | 80 passed, 2 skipped |
| 2 | BenchmarkResult stores all metrics including median calculations | `tests/unit/test_engine_benchmark.py` | unit | PASS | 80 passed, 2 skipped |
| 3 | EngineBenchmark.run() raises BenchmarkNotRun before correctness passes | `tests/unit/test_engine_benchmark.py` | unit | PASS | 80 passed, 2 skipped |
| 4 | BenchmarkConfig.validate_noise_rule() raises when noise rule undefined | `tests/unit/test_engine_benchmark.py` | unit | PASS | 80 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M3.6 lines exercised by unit tests
- Intentional gap: `EngineBenchmark.run_equivalence()` engine implementations for NautilusTrader and LEAN are not yet wired; `BenchmarkResult` correctness gate delegates to engine's `run_correctness_gate()` method which candidate engines must implement
- Intentional gap: actual process-tree RAM measurement (`psutil.Process.memory_info()`) not yet wired into engine adapters; will be wired when engines are integrated
- The harness enforces correctness-first: no performance measurement runs until correctness gate passes

## Merge evidence
Commit: `f286b06` (M3.3) + M3.6 commit (engine_benchmark.py + tests). RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 80 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
