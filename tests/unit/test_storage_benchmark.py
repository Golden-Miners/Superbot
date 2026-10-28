"""RED tests for M2.6 — OHLCV storage format benchmark abstraction.

Defines the testable contract for a storage benchmark harness:
- register a storage format backend
- write/read a representative OHLCV dataset
- measure write time, read time, compressed size
- compare formats and return comparable metrics

No actual benchmark runs or storage writes happen at import time.
"""

from __future__ import annotations

import pytest

from superbot.data.storage_benchmark import (
    BenchmarkResult,
    StorageBackend,
    StorageBenchmark,
    UnknownFormatError,
)


def test_benchmark_result_fields():
    r = BenchmarkResult(
        format="parquet",
        write_time_ms=12.5,
        read_time_ms=3.2,
        compressed_bytes=1024,
        bar_count=1000,
    )
    assert r.format == "parquet"
    assert r.write_time_ms == 12.5
    assert r.read_time_ms == 3.2
    assert r.compressed_bytes == 1024
    assert r.bar_count == 1000


def test_run_benchmark_unknown_format_raises():
    bench = StorageBenchmark()
    with pytest.raises(UnknownFormatError):
        bench.run_benchmark("nonexistent", bar_count=10)


def test_register_duplicate_format_raises():
    bench = StorageBenchmark()
    bench.register(
        "parquet", StorageBackend(write=lambda bars: None, read=lambda p: [], size_bytes=lambda: 0)
    )
    with pytest.raises(UnknownFormatError):
        bench.register(
            "parquet",
            StorageBackend(write=lambda bars: None, read=lambda p: [], size_bytes=lambda: 0),
        )


def test_benchmark_returns_comparable_metrics():
    bench = StorageBenchmark()
    bench.register(
        "parquet",
        StorageBackend(
            write=lambda bars: None,
            read=lambda path: [],
            size_bytes=lambda: 500,
        ),
    )
    result = bench.run_benchmark("parquet", bar_count=100)
    assert isinstance(result, BenchmarkResult)
    assert result.format == "parquet"
    assert result.bar_count == 100
    assert result.write_time_ms >= 0
    assert result.read_time_ms >= 0
    assert result.compressed_bytes >= 0
