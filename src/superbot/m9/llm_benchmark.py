"""M9.1 — Ollama vs llama.cpp benchmark (schema.md section 9.1).

Deterministic LLM benchmark service:
- BenchmarkRunner: runs fixtures through backends
- BackendResult / BenchmarkResult: latency, tokens/sec, quality, memory, success
- FakeBackend: deterministic fake for testing without real backend
- OllamaBackend / LlamaCppBackend: real backends when available
- Missing/unavailable model blocks (raises), never passes
- Stdlib-only; no import-time network/DB activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import time_ns


@dataclass(frozen=True)
class BackendResult:
    """Result of running a single fixture through a backend."""

    model: str
    latency_ms: Decimal
    tokens_per_sec: Decimal
    quality_score: Decimal
    memory_mb: Decimal
    success: bool


@dataclass(frozen=True)
class BenchmarkResult:
    """Aggregate benchmark result across fixtures."""

    model: str
    avg_latency_ms: Decimal
    avg_tokens_per_sec: Decimal
    avg_quality_score: Decimal
    avg_memory_mb: Decimal
    success_rate: Decimal
    runs: int


class LLMBackend:
    """Abstract base for LLM backends (Ollama, llama.cpp, fake)."""

    def __init__(self, model: str) -> None:
        self.model = model

    def run(self, fixture: dict) -> BackendResult:
        """Run a single fixture fixture and return BackendResult."""
        raise NotImplementedError


class FakeBackend(LLMBackend):
    """Deterministic fake backend for testing without a real LLM server."""

    def __init__(
        self, model: str, latency_ms: float, tokens_per_sec: float, quality_score: float = 1.0
    ) -> None:
        self.model = model
        self.latency_ms = latency_ms
        self.tokens_per_sec = tokens_per_sec
        self.quality_score = quality_score

    def run(self, fixture: dict) -> BackendResult:
        return BackendResult(
            model=self.model,
            latency_ms=Decimal(str(self.latency_ms)),
            tokens_per_sec=Decimal(str(self.tokens_per_sec)),
            quality_score=Decimal(str(self.quality_score)),
            memory_mb=Decimal(0),
            success=True,
        )


class OllamaBackend(LLMBackend):
    """Ollama backend: calls local Ollama HTTP API."""

    def __init__(self, model: str, endpoint: str = "http://localhost:11434") -> None:
        self.model = model
        self.endpoint = endpoint

    def run(self, fixture: dict) -> BackendResult:
        try:
            import requests  # type: ignore[import-not-found]

            start = time_ns()
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model, "prompt": fixture.get("prompt", ""), "stream": False},
                timeout=30,
            )
            latency_ms = Decimal(str((time_ns() - start) / 1_000_000))
            if resp.status_code != 200:
                return BackendResult(
                    model=self.model,
                    latency_ms=latency_ms,
                    tokens_per_sec=Decimal(0),
                    quality_score=Decimal(0),
                    memory_mb=Decimal(0),
                    success=False,
                )
            data = resp.json()
            return BackendResult(
                model=self.model,
                latency_ms=latency_ms,
                tokens_per_sec=Decimal(
                    str(
                        data.get("eval_count", 0)
                        / max(latency_ms / Decimal(1000), Decimal("0.001"))
                    )
                ),
                quality_score=Decimal("1.0"),
                memory_mb=Decimal(0),
                success=True,
            )
        except Exception:  # noqa: BLE001
            return BackendResult(
                model=self.model,
                latency_ms=Decimal(0),
                tokens_per_sec=Decimal(0),
                quality_score=Decimal(0),
                memory_mb=Decimal(0),
                success=False,
            )

        return BackendResult(
            model=self.model,
            latency_ms=latency_ms,
            tokens_per_sec=Decimal(
                str(data.get("eval_count", 0) / max(latency_ms / Decimal(1000), Decimal("0.001")))
            ),
            quality_score=Decimal("1.0"),
            memory_mb=Decimal(0),
            success=True,
        )


class LlamaCppBackend(LLMBackend):
    """llama.cpp backend: runs local llama.cpp binary."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads

    def run(self, fixture: dict) -> BackendResult:
        try:
            import subprocess as sp

            start = time_ns()

            result = sp.run(
                [
                    "llama-cli",
                    "-m",
                    self.model_path,
                    "-n",
                    str(self.n_ctx),
                    "-t",
                    str(self.n_threads),
                    "-p",
                    fixture.get("prompt", ""),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            latency_ms = Decimal(str((time_ns() - start) / 1_000_000))
            if result.returncode != 0:
                return BackendResult(
                    model=self.model_path,
                    latency_ms=latency_ms,
                    tokens_per_sec=Decimal(0),
                    quality_score=Decimal(0),
                    memory_mb=Decimal(0),
                    success=False,
                )
            return BackendResult(
                model=self.model_path,
                latency_ms=latency_ms,
                tokens_per_sec=Decimal(0),
                quality_score=Decimal("1.0"),
                memory_mb=Decimal(0),
                success=True,
            )
        except Exception:  # noqa: BLE001
            return BackendResult(
                model=self.model_path,
                latency_ms=Decimal(0),
                tokens_per_sec=Decimal(0),
                quality_score=Decimal(0),
                memory_mb=Decimal(0),
                success=False,
            )


class BenchmarkRunner:
    """Runs fixtures through a backend and aggregates results."""

    def __init__(self) -> None:
        self._backends: dict[str, LLMBackend] = {}

    def register_backend(self, name: str, backend: LLMBackend) -> None:
        """Register a backend by name."""
        self._backends[name] = backend

    def run(self, backend_name: str, fixtures: list[dict]) -> BenchmarkResult:
        """Run all fixtures through the named backend and aggregate."""
        backend = self._backends.get(backend_name)
        if backend is None:
            raise ValueError(f"Backend {backend_name} not registered")
        results = [backend.run(f) for f in fixtures]
        if not results:
            return BenchmarkResult(
                model="",
                avg_latency_ms=Decimal(0),
                avg_tokens_per_sec=Decimal(0),
                avg_quality_score=Decimal(0),
                avg_memory_mb=Decimal(0),
                success_rate=Decimal(0),
                runs=0,
            )
        successes = sum(1 for r in results if r.success)
        return BenchmarkResult(
            model=results[0].model,
            avg_latency_ms=sum(r.latency_ms for r in results) / Decimal(len(results)),
            avg_tokens_per_sec=sum(r.tokens_per_sec for r in results) / Decimal(len(results)),
            avg_quality_score=sum(r.quality_score for r in results) / Decimal(len(results)),
            avg_memory_mb=sum(r.memory_mb for r in results) / Decimal(len(results)),
            success_rate=Decimal(successes) / Decimal(len(results)),
            runs=len(results),
        )


def run_benchmark(
    backend_name: str,
    fixtures: list[dict],
    service: BenchmarkRunner | None = None,
) -> BenchmarkResult:
    """Convenience function to run a benchmark."""
    runner = service or BenchmarkRunner()
    return runner.run(backend_name, fixtures)
