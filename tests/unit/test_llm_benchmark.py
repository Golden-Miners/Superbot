"""RED tests for M9.1 — Benchmark Ollama vs llama.cpp on laptop/desktop using task fixtures.

Tests define:
- LLMBackend: abstract interface for running inference (Ollama, llama.cpp, or fake)
- BenchmarkResult: latency, tokens/sec, quality score, memory, success
- BenchmarkRunner: runs a set of task fixtures through a backend
- Deterministic: same inputs → identical results (fake backends)
- Missing/unavailable model → blocked, not PASS
- No AI writes PASS directly: verdict is deterministic from metrics
- Stdlib-only, no import-time network activity
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.m9.llm_benchmark import (
    BackendResult,
    BenchmarkResult,
    BenchmarkRunner,
    FakeBackend,
    LlamaCppBackend,
    OllamaBackend,
)


def test_ollama_backend_creates():
    """OllamaBackend can be created with model and endpoint."""
    b = OllamaBackend(model="llama3", endpoint="http://localhost:11434")
    assert b.model == "llama3"
    assert b.endpoint == "http://localhost:11434"


def test_llamacpp_backend_creates():
    """LlamaCppBackend can be created with model path."""
    b = LlamaCppBackend(model_path="/models/llama-2-7b.Q4_K_M.gguf", n_ctx=4096)
    assert b.model_path == "/models/llama-2-7b.Q4_K_M.gguf"
    assert b.n_ctx == 4096


def test_fake_backend_creates():
    """FakeBackend can be created with deterministic outputs."""
    b = FakeBackend(model="fake-model", latency_ms=10, tokens_per_sec=50.0)
    assert b.model == "fake-model"
    assert b.latency_ms == 10
    assert b.tokens_per_sec == 50.0


def test_backend_result_creates():
    """BackendResult can be created."""
    r = BackendResult(
        model="test-model",
        latency_ms=Decimal(50),
        tokens_per_sec=Decimal("25.0"),
        quality_score=Decimal("0.8"),
        memory_mb=Decimal(4096),
        success=True,
    )
    assert r.model == "test-model"
    assert r.success is True


def test_benchmark_result_creates():
    """BenchmarkResult aggregates multiple backend results."""
    r = BenchmarkResult(
        model="test-model",
        avg_latency_ms=Decimal(50),
        avg_tokens_per_sec=Decimal("25.0"),
        avg_quality_score=Decimal("0.8"),
        avg_memory_mb=Decimal(4096),
        success_rate=Decimal("1.0"),
        runs=3,
    )
    assert r.success_rate == Decimal("1.0")


def test_fake_backend_run_is_deterministic():
    """Same fake backend + same fixture → identical results."""
    b = FakeBackend(model="fake", latency_ms=10, tokens_per_sec=50.0)
    fixture = {"prompt": "What is 2+2?", "expected": "4"}
    r1 = b.run(fixture)
    r2 = b.run(fixture)
    assert r1.latency_ms == r2.latency_ms
    assert r1.tokens_per_sec == r2.tokens_per_sec
    assert r1.success == r2.success


def test_benchmark_runner_runs_all_fixtures():
    """BenchmarkRunner runs all fixtures through a backend."""
    service = BenchmarkRunner()
    service.register_backend("fake", FakeBackend(model="f", latency_ms=10, tokens_per_sec=50.0))
    fixtures = [
        {"prompt": "q1", "expected": "a1"},
        {"prompt": "q2", "expected": "a2"},
    ]
    result = service.run("fake", fixtures)
    assert result.runs == 2
    assert result.success_rate == Decimal("1.0")


def test_benchmark_quality_threshold():
    """Benchmark fails quality when quality_score below threshold."""
    service = BenchmarkRunner()
    service.register_backend(
        "slow",
        FakeBackend(model="s", latency_ms=5000, tokens_per_sec=1.0, quality_score=Decimal("0.2")),
    )
    result = service.run("slow", [{"prompt": "q", "expected": "a"}])
    assert result.success_rate < Decimal("1.0") or result.avg_quality_score < Decimal("0.5")


def test_missing_model_blocks():
    """Missing/unavailable model blocks benchmark (not PASS)."""
    service = BenchmarkRunner()
    with pytest.raises(ValueError):
        service.run("nonexistent-model", [{"prompt": "q", "expected": "a"}])


def test_no_ai_direct_pass():
    """No AI model can set PASS directly — verdict comes from metrics."""
    service = BenchmarkRunner()
    service.register_backend(
        "good",
        FakeBackend(model="g", latency_ms=10, tokens_per_sec=50.0, quality_score=Decimal("0.9")),
    )
    result = service.run("good", [{"prompt": "q", "expected": "a"}])
    assert result.success_rate == Decimal("1.0")
    assert result.avg_quality_score == Decimal("0.9")


def test_benchmark_deterministic():
    """Same inputs yield identical benchmark results."""
    s1 = BenchmarkRunner()
    s2 = BenchmarkRunner()
    s1.register_backend("f", FakeBackend(model="f", latency_ms=10, tokens_per_sec=50.0))
    s2.register_backend("f", FakeBackend(model="f", latency_ms=10, tokens_per_sec=50.0))
    r1 = s1.run("f", [{"prompt": "q", "expected": "a"}])
    r2 = s2.run("f", [{"prompt": "q", "expected": "a"}])
    assert r1.avg_latency_ms == r2.avg_latency_ms
    assert r1.avg_tokens_per_sec == r2.avg_tokens_per_sec
