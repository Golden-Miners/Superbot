"""Storage format benchmark abstraction (M2.6).

Defines a testable contract for benchmarking OHLCV storage formats
(Parquet and alternatives) on representative data. No storage writes or
benchmark runs happen at import time; backends are registered explicitly.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass


class UnknownFormatError(ValueError):
    """Raised when a requested storage format is not registered."""


@dataclass(frozen=True)
class StorageBackend:
    """A storage format backend.

    write(bars) -> None        persist bars and return nothing
    read(path) -> Iterable     load bars back
    size_bytes() -> int        compressed on-disk size in bytes
    """

    write: Callable[[list], None]
    read: Callable[[str], Iterable]
    size_bytes: Callable[[], int]


@dataclass(frozen=True)
class BenchmarkResult:
    """Comparable metrics for one storage format run."""

    format: str
    write_time_ms: float
    read_time_ms: float
    compressed_bytes: int
    bar_count: int


class StorageBenchmark:
    """Registers storage backends and runs comparable benchmarks."""

    def __init__(self) -> None:
        self._backends: dict[str, StorageBackend] = {}

    def register(self, format: str, backend: StorageBackend) -> None:
        if format in self._backends:
            raise UnknownFormatError(f"format {format!r} already registered")
        self._backends[format] = backend

    def run_benchmark(self, format: str, bar_count: int) -> BenchmarkResult:
        backend = self._backends.get(format)
        if backend is None:
            raise UnknownFormatError(f"format {format!r} not registered")

        bars = [{"i": i} for i in range(bar_count)]

        start = time.perf_counter()
        backend.write(bars)
        write_ms = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        list(backend.read("unused_path"))
        read_ms = (time.perf_counter() - start) * 1000.0

        size = backend.size_bytes()

        return BenchmarkResult(
            format=format,
            write_time_ms=write_ms,
            read_time_ms=read_ms,
            compressed_bytes=size,
            bar_count=bar_count,
        )
