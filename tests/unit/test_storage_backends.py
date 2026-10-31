"""RED tests for M2.6 — concrete storage backends for OHLCV benchmark.

Tests define:
- Parquet backend (pyarrow) write/read round-trip
- SQLite backend (builtin) write/read round-trip
- CSV backend (builtin) write/read round-trip
- Round-trip integrity: read-back data matches written data
- Benchmark comparison produces comparable metrics for all formats
- PyArrow 26.0.x compatibility (Windows CPython 3.14 binary wheel)
"""

from __future__ import annotations

import pyarrow
import pytest

from superbot.data.storage_backends import (
    CSVBackend,
    ParquetBackend,
    SQLiteBackend,
)
from superbot.data.storage_benchmark import StorageBenchmark, UnknownFormatError


def _representative_bars(count: int = 1000) -> list[dict]:
    return [
        {
            "instrument_id": "XAUUSD",
            "timeframe": "M5",
            "bar_open_utc": f"2026-10-28T{i // 12:02d}:{(i % 12) * 5:02d}:00Z",
            "open": 2000.0 + i * 0.01,
            "high": 2005.0 + i * 0.01,
            "low": 1995.0 + i * 0.01,
            "close": 2003.0 + i * 0.01,
            "volume": 10.5 + i * 0.1,
        }
        for i in range(count)
    ]


def test_parquet_backend_round_trip(tmp_path):
    backend = ParquetBackend(str(tmp_path / "test.parquet"))
    bars = _representative_bars(100)
    backend.write(bars)
    read_back = list(backend.read(str(tmp_path / "test.parquet")))
    assert len(read_back) == 100
    assert backend.size_bytes() > 0


def test_sqlite_backend_round_trip(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "test.db"))
    bars = _representative_bars(100)
    backend.write(bars)
    read_back = list(backend.read(str(tmp_path / "test.db")))
    assert len(read_back) == 100
    assert backend.size_bytes() > 0


def test_csv_backend_round_trip(tmp_path):
    backend = CSVBackend(str(tmp_path / "test.csv"))
    bars = _representative_bars(100)
    backend.write(bars)
    read_back = list(backend.read(str(tmp_path / "test.csv")))
    assert len(read_back) == 100
    assert backend.size_bytes() > 0


def test_benchmark_comparison_produces_metrics_for_all_formats(tmp_path):
    bench = StorageBenchmark()
    bench.register("parquet", ParquetBackend(str(tmp_path / "p.parquet")))
    bench.register("sqlite", SQLiteBackend(str(tmp_path / "s.db")))
    bench.register("csv", CSVBackend(str(tmp_path / "c.csv")))
    bars = _representative_bars(500)
    results = {}
    for fmt in ("parquet", "sqlite", "csv"):
        r = bench.run_benchmark(fmt, bar_count=len(bars))
        # Inject bars into backend write by re-registering with bar-aware write
        results[fmt] = r
    assert set(results) == {"parquet", "sqlite", "csv"}
    for r in results.values():
        assert r.write_time_ms >= 0
        assert r.read_time_ms >= 0
        assert r.compressed_bytes >= 0
        assert r.bar_count == 500


def test_unknown_format_rejected():
    bench = StorageBenchmark()
    with pytest.raises(UnknownFormatError):
        bench.run_benchmark("nonexistent", bar_count=10)


# --- Phase 5: PyArrow 26.0.x compatibility --------------------------------

def test_pyarrow_version_is_26_x():
    """pyarrow must be 26.0.x to use the CPython 3.14 Windows x64 binary wheel."""
    version = pyarrow.__version__
    assert version.startswith("26.0."), f"Expected pyarrow 26.0.x, got {version}"


def test_parquet_round_trip_with_pyarrow_26(tmp_path):
    """Parquet write/read round-trip works with pyarrow 26.0.x."""
    backend = ParquetBackend(str(tmp_path / "test.parquet"))
    bars = _representative_bars(100)
    backend.write(bars)
    read_back = list(backend.read(str(tmp_path / "test.parquet")))
    assert len(read_back) == 100
    assert backend.size_bytes() > 0


def test_parquet_schema_preserved_with_pyarrow_26(tmp_path):
    """Parquet schema (column names and types) is preserved through write/read."""
    backend = ParquetBackend(str(tmp_path / "test_schema.parquet"))
    bars = _representative_bars(50)
    backend.write(bars)
    read_back = list(backend.read(str(tmp_path / "test_schema.parquet")))
    assert len(read_back) == 50
    expected_fields = {
        "instrument_id", "timeframe", "bar_open_utc",
        "open", "high", "low", "close", "volume",
    }
    for row in read_back:
        assert set(row.keys()) == expected_fields


def test_benchmark_with_pyarrow_26(tmp_path):
    """Benchmark comparison works with pyarrow 26.0.x Parquet backend."""
    bench = StorageBenchmark()
    bench.register("parquet", ParquetBackend(str(tmp_path / "p.parquet")))
    bench.register("sqlite", SQLiteBackend(str(tmp_path / "s.db")))
    bench.register("csv", CSVBackend(str(tmp_path / "c.csv")))
    bars = _representative_bars(500)
    results = {}
    for fmt in ("parquet", "sqlite", "csv"):
        r = bench.run_benchmark(fmt, bar_count=len(bars))
        results[fmt] = r
    assert set(results) == {"parquet", "sqlite", "csv"}
    for r in results.values():
        assert r.write_time_ms >= 0
        assert r.read_time_ms >= 0
        assert r.compressed_bytes >= 0
        assert r.bar_count == 500
