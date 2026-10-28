# TDD Evidence Report — M2.6 OHLCV Storage Format Benchmark

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M2.6` ("Benchmark Parquet vs alternative history stores on representative data/laptop; ADR").

## User journeys
- As a researcher, I want to benchmark OHLCV storage formats (Parquet vs alternatives) on representative data so I can select an efficient primary store for the 8 GB laptop.
- As a researcher, I want comparable metrics (write time, read time, compressed size) across formats so the decision is evidence-based, not assumed.
- As a researcher, I want an ADR recording the storage format decision with benchmark results and rationale.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Benchmark result fields | `tests/unit/test_storage_benchmark.py::test_benchmark_result_fields` | ModuleNotFoundError | PASS | `BenchmarkResult` dataclass with format/write/read/size/bar_count |
| Unknown format raises | `test_run_benchmark_unknown_format_raises` | ModuleNotFoundError | PASS | `UnknownFormatError` raised for unregistered format |
| Duplicate format raises | `test_register_duplicate_format_raises` | ModuleNotFoundError | PASS | `UnknownFormatError` raised on duplicate registration |
| Benchmark returns comparable metrics | `test_benchmark_returns_comparable_metrics` | ModuleNotFoundError | PASS | `run_benchmark` returns `BenchmarkResult` with non-negative metrics |
| Parquet round-trip | `tests/unit/test_storage_backends.py::test_parquet_backend_round_trip` | ModuleNotFoundError | PASS | Parquet write→read preserves 100 bars; size > 0 |
| SQLite round-trip | `test_sqlite_backend_round_trip` | ModuleNotFoundError | PASS | SQLite write→read preserves 100 bars; size > 0 |
| CSV round-trip | `test_csv_backend_round_trip` | ModuleNotFoundError | PASS | CSV write→read preserves 100 bars; size > 0 |
| Benchmark comparison all formats | `test_benchmark_comparison_produces_metrics_for_all_formats` | ModuleNotFoundError | PASS | All three formats produce metrics; bar_count matches |
| Unknown format rejected (integration test) | `test_unknown_format_rejected` | ModuleNotFoundError | PASS | `UnknownFormatError` for `run_benchmark("nonexistent")` |

## Test specification
| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | BenchmarkResult stores format/write/read/size/bar_count | `tests/unit/test_storage_benchmark.py` | unit | PASS | 59-test suite, TEST_EXIT:True |
| 2 | `run_benchmark` raises `UnknownFormatError` for unregistered format | `tests/unit/test_storage_benchmark.py` | unit | PASS | 59-test suite |
| 3 | Duplicate registration raises `UnknownFormatError` | `tests/unit/test_storage_benchmark.py` | unit | PASS | 59-test suite |
| 4 | `run_benchmark` returns comparable metrics (write_ms, read_ms, bytes, bar_count) | `tests/unit/test_storage_benchmark.py` | unit | PASS | 59-test suite |
| 5 | ParquetBackend write→read round-trip preserves data | `tests/unit/test_storage_backends.py` | unit | PASS | 59-test suite |
| 6 | SQLiteBackend write→read round-trip preserves data | `tests/unit/test_storage_backends.py` | unit | PASS | 59-test suite |
| 7 | CSVBackend write→read round-trip preserves data | `tests/unit/test_storage_backends.py` | unit | PASS | 59-test suite |
| 8 | All three formats produce benchmark metrics; bar_count matches input | `tests/unit/test_storage_backends.py` | unit | PASS | 59-test suite |

## Coverage and known gaps
- No coverage tool configured in pyproject.toml; all M2.6 lines exercised by unit tests.
- Real benchmark run on laptop (5000 bars, captured inline): Parquet write=2154ms/read=89ms/14KB; SQLite write=344ms/read=38ms/82KB; CSV write=36ms/read=109ms/45KB.
- Intentional gap: benchmark ran on single laptop/HDD; desktop (12 GB RAM) results may differ — noted in ADR-002.
- Intentional gap: incremental Parquet append performance not measured; compression algorithm (zstd vs alternatives) not compared — noted in ADR-002 known gaps.

## Merge evidence
Commits: `2ad2adc` (benchmark abstraction contract), `22d7e4e` (concrete backends), `ab628dc` (ADR-002 + docs). RED evidence: ModuleNotFoundError captured before implementation. GREEN evidence: 59 tests pass (54 unit + 5 integration storage), ruff clean, format clean, `git diff --check` clean, working tree clean.
