"""Concrete OHLCV storage backends for M2.6 benchmark.

- ParquetBackend: pyarrow Parquet (compressed columnar)
- SQLiteBackend: builtin sqlite3 (row store)
- CSVBackend: builtin csv (row store, uncompressed)

All import-safe: no storage writes happen at import time.
"""

from __future__ import annotations

import csv
import os
import sqlite3
from collections.abc import Iterable

import pyarrow as pa
import pyarrow.parquet as pq


class ParquetBackend:
    """Parquet storage backend using pyarrow."""

    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, bars: list[dict]) -> None:
        if bars:
            table = pa.Table.from_pylist(bars)
        else:
            table = pa.table({})
        pq.write_table(table, self.path, compression="zstd")

    def read(self, path: str | None = None) -> Iterable[dict]:
        target = path or self.path
        table = pq.read_table(target)
        return table.to_pylist()

    def size_bytes(self) -> int:
        return os.path.getsize(self.path)


class SQLiteBackend:
    """SQLite storage backend using builtin sqlite3."""

    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, bars: list[dict]) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                "CREATE TABLE bars ("
                "instrument_id TEXT, timeframe TEXT, bar_open_utc TEXT,"
                " open REAL, high REAL, low REAL, close REAL, volume REAL)"
            )
            conn.executemany(
                "INSERT INTO bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        b.get("instrument_id"),
                        b.get("timeframe"),
                        b.get("bar_open_utc"),
                        b.get("open"),
                        b.get("high"),
                        b.get("low"),
                        b.get("close"),
                        b.get("volume"),
                    )
                    for b in bars
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def read(self, path: str | None = None) -> Iterable[dict]:
        target = path or self.path
        conn = sqlite3.connect(target)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT instrument_id, timeframe, bar_open_utc, open, high, "
                "low, close, volume FROM bars"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def size_bytes(self) -> int:
        return os.path.getsize(self.path)


class CSVBackend:
    """CSV storage backend using builtin csv (uncompressed)."""

    FIELDS = (
        "instrument_id",
        "timeframe",
        "bar_open_utc",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, bars: list[dict]) -> None:
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDS)
            writer.writeheader()
            for b in bars:
                writer.writerow({k: b.get(k) for k in self.FIELDS})

    def read(self, path: str | None = None) -> Iterable[dict]:
        target = path or self.path
        with open(target, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def size_bytes(self) -> int:
        return os.path.getsize(self.path)
