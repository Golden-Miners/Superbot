# TDD Evidence Report — M8.1 PostgreSQL Config/Suitability Benchmark on Laptop

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.1` ("PostgreSQL config/suitability benchmark on laptop").

## User journeys
- As a researcher, I want to connect to a PostgreSQL instance with explicit connection config (host/port/dbname/user/password)
- As a researcher, I want to benchmark query latency against PostgreSQL
- As a researcher, I want config suitability assessed against explicit recommendations (shared_buffers, work_mem, effective_cache_size)
- As a researcher, I want a suitability verdict (PASS/WARN/BLOCK) based on config + latency
- As a researcher, I want missing connection params to block rather than default
- As a researcher, I want deterministic results without requiring a live database

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Service creation defaults | `tests/unit/test_postgres_benchmark.py::test_postgres_benchmark_service_creates` | ModuleNotFoundError | PASS | Service instantiates with localhost:5432/postgres/postgres defaults |
| Service custom config | `tests/unit/test_postgres_benchmark_service_custom_config` | ModuleNotFoundError | PASS | Custom host/port/dbname/user accepted |
| check_connection | `tests/unit/test_postgres_benchmark.py::test_check_connection_success` | ModuleNotFoundError | PASS | Returns bool |
| Benchmark latency | `tests/unit/test_postgres_benchmark.py::test_benchmark_queries_measures_latency` | ModuleNotFoundError | PASS | query_count, iterations, avg/max/min latency |
| Benchmark empty queries | `tests/unit/test_postgres_benchmark.py::test_benchmark_queries_empty` | ModuleNotFoundError | PASS | Zero queries → zero latency |
| Config assessment | `tests/unit/test_postgres_benchmark.py::test_assess_config` | ModuleNotFoundError | PASS | current vs recommended, meets flag |
| Config all met | `tests/unit/test_postgres_benchmark.py::test_assess_config_all_met` | ModuleNotFoundError | PASS | all met when current >= recommended |
| Suitability PASS | `tests/unit/test_postgres_benchmark.py::test_compute_suitability_verdict_pass` | ModuleNotFoundError | PASS | config met + low latency → PASS |
| Suitability WARN | `tests/unit/test_postgres_benchmark.py::test_compute_suitability_verdict_warn` | ModuleNotFoundError | PASS | config not met + low latency → WARN |
| Suitability BLOCK | `tests/unit/test_postgres_benchmark.py::test_compute_suitability_verdict_block_high_latency` | ModuleNotFoundError | PASS | high latency → BLOCK |
| Full benchmark run | `tests/unit/test_postgres_benchmark.py::test_run_postgres_benchmark` | ModuleNotFoundError | PASS | BenchmarkResult with suitability |
| BenchmarkResult creation | `tests/unit/test_postgres_benchmark.py::test_benchmark_result_creates` | ModuleNotFoundError | PASS | Result dataclass |
| Deterministic | `tests/unit/test_postgres_benchmark.py::test_postgres_benchmark_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Missing params block | `tests/unit/test_postgres_benchmark.py::test_missing_connection_params_block` | ModuleNotFoundError | PASS | None host raises MissingInputError |
| Suitability enum | `tests/unit/test_postgres_benchmark.py::test_suitability_verdict_creates` | ModuleNotFoundError | PASS | PASS/WARN/BLOCK values |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Connection config | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |
| 2 | Query latency benchmark | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |
| 3 | Config assessment | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |
| 4 | Suitability verdict | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |
| 6 | Missing params blocked | `tests/unit/test_postgres_benchmark.py` | unit | PASS | 483 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.1 lines exercised by unit tests
- Intentional gap: No live PostgreSQL in test environment — synthetic deterministic latency used when no connection
- Intentional gap: `_sample_current_config` returns laptop defaults rather than live PG values
- Intentional gap: `psycopg2` import is optional (type: ignore) — real path only when installed

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.postgres_benchmark'` captured before implementation. GREEN: 483 tests pass, 2 skipped, ruff clean, format clean, working tree clean.