# ADR-002: OHLCV Market-History Storage Format

**Status:** Accepted  
**Date:** 2026-10-29  
**Scope:** M2.6 — market-history store format decision

## Decision

Use **Parquet (zstd-compressed)** as the primary OHLCV market-history store for Superbot. SQLite remains available as a secondary format for the application database (PostgreSQL is the selected app DB per PRD §2). CSV is retained only as an interchange/export format, not a primary store.

## Context

M2.6 required benchmarking OHLCV storage formats on representative data on the target laptop (Windows 10, ~8 GB RAM, 2 logical CPU threads, HDD). The benchmark harness (`src/superbot/data/storage_benchmark.py`) registers backends and returns comparable metrics: write time, read time, compressed size, bar count.

Three backends were implemented and tested (`src/superbot/data/storage_backends.py`):
- `ParquetBackend` — pyarrow Parquet with zstd compression
- `SQLiteBackend` — builtin sqlite3 row store
- `CSVBackend` — builtin csv uncompressed row store

## Benchmark results (5,000 synthetic OHLCV bars, laptop HDD)

| Format | Write time | Read time | Compressed size | Notes |
|--------|-----------|-----------|-----------------|-------|
| Parquet (zstd) | 2154 ms | 89 ms | 14,133 bytes | Best compression; write includes pyarrow cold-start |
| SQLite | 344 ms | 38 ms | 81,920 bytes | Fastest read; largest size |
| CSV | 36 ms | 109 ms | 45,065 bytes | Fastest write; no compression |

Round-trip read-back integrity verified for all three formats (unit tests in `tests/unit/test_storage_backends.py`).

## Rationale

- **Compression/size:** Parquet is ~3.2x smaller than CSV and ~5.8x smaller than SQLite. Market history grows unboundedly over time; storage efficiency matters on an 8 GB laptop with HDD.
- **Read performance:** Parquet read (89 ms) is acceptable for research/validation workloads; SQLite is faster (38 ms) but at 5.8x the storage cost.
- **Write performance:** CSV writes fastest but Parquet's write cost is dominated by one-time pyarrow cold-start; incremental/append workloads were not benchmarked and remain a known gap.
- **Laptop fit:** Smallest on-disk footprint is most important for the 8 GB RAM / HDD target machine.

Parquet's compression advantage and acceptable read latency make it the best primary store for market history on this hardware.

## Alternatives considered

- **SQLite:** Rejected as primary store — largest on-disk footprint (82 KB for 5K bars), no columnar compression. Acceptable as an application metadata store but PostgreSQL is already selected for that role (PRD §2).
- **CSV:** Rejected as primary store — no compression (45 KB), slowest read (109 ms). Retained for interchange/export only.
- **DuckDB:** Not available on this laptop (import fails); not benchmarked. Could be re-evaluated later.

## Consequences

- `src/superbot/data/storage_benchmark.py` — benchmark harness contract (`StorageBenchmark`, `StorageBackend`, `BenchmarkResult`, `UnknownFormatError`).
- `src/superbot/data/storage_backends.py` — three concrete backends (`ParquetBackend`, `SQLiteBackend`, `CSVBackend`).
- Primary OHLCV history writes/reads use Parquet (zstd).
- No import-time storage writes; backends registered explicitly.
- Benchmark results are specific to this laptop/HDD; results may differ on the desktop target (12 GB RAM). Re-benchmark before any desktop deployment decision.

## Known gaps

- Incremental append performance for Parquet not measured (full rewrite per benchmark run).
- Benchmark ran on a single machine; no cross-machine comparison.
- Compression algorithm (zstd) not compared against alternatives (snappy, gzip, lz4).
