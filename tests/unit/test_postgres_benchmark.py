"""RED tests for M8.1 — PostgreSQL config/suitability benchmark on laptop.

Tests define:
- PostgreSQLBenchmarkService: runs config/suitability benchmark against a PostgreSQL instance
- BenchmarkResult: benchmark outcome with latency, config assessment, suitability verdict
- Connection testing: can connect to PostgreSQL with given config
- Query benchmarking: measures latency of representative queries
- Config suitability: checks key PostgreSQL config params (shared_buffers, work_mem, etc.)
- Suitability verdict: PASS/WARN/BLOCK based on config and latency thresholds
- Missing connection params block rather than defaulting
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/DB activity
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.persistence.postgres_benchmark import (
    BenchmarkResult,
    ConfigAssessment,
    MissingInputError,
    PostgreSQLBenchmarkService,
    SuitabilityVerdict,
    assess_config,
    benchmark_queries,
    check_connection,
    compute_suitability_verdict,
    run_postgres_benchmark,
)


def test_postgres_benchmark_service_creates():
    """PostgreSQLBenchmarkService can be created with default config."""
    service = PostgreSQLBenchmarkService()
    assert service is not None


def test_postgres_benchmark_service_custom_config():
    """PostgreSQLBenchmarkService accepts custom connection config."""
    service = PostgreSQLBenchmarkService(
        host="localhost",
        port=5432,
        dbname="superbot",
        user="superbot",
        password="secret",
        connect_timeout=5,
    )
    assert service.host == "localhost"
    assert service.port == 5432
    assert service.dbname == "superbot"
    assert service.user == "superbot"


def test_check_connection_success():
    """check_connection returns True when connection succeeds."""
    result = check_connection(
        host="localhost",
        port=5432,
        dbname="superbot",
        user="superbot",
        password="secret",
        connect_timeout=1,
    )
    assert isinstance(result, bool)


def test_benchmark_queries_measures_latency():
    """benchmark_queries measures latency of representative queries."""
    result = benchmark_queries(
        queries=["SELECT 1", "SELECT COUNT(*) FROM pg_database"],
        iterations=3,
    )
    assert result.query_count == 2
    assert result.iterations == 3
    assert result.avg_latency_ms >= Decimal(0)
    assert result.max_latency_ms >= result.avg_latency_ms
    assert result.min_latency_ms <= result.avg_latency_ms


def test_benchmark_queries_empty():
    """benchmark_queries with no queries returns zero latency."""
    result = benchmark_queries(queries=[], iterations=1)
    assert result.query_count == 0
    assert result.avg_latency_ms == Decimal(0)


def test_config_assessment_creates():
    """ConfigAssessment can be created."""
    ca = ConfigAssessment(
        param_name="shared_buffers",
        current_value="128MB",
        recommended_value="256MB",
        meets_recommendation=False,
    )
    assert ca.param_name == "shared_buffers"
    assert ca.meets_recommendation is False


def test_assess_config():
    """assess_config evaluates PostgreSQL config params against recommendations."""
    current_config = {
        "shared_buffers": "128MB",
        "work_mem": "4MB",
        "effective_cache_size": "1GB",
    }
    recommendations = {
        "shared_buffers": "256MB",
        "work_mem": "16MB",
        "effective_cache_size": "2GB",
    }
    result = assess_config(current_config, recommendations)
    assert len(result) == 3
    # shared_buffers: 128MB < 256MB -> not met
    assert result["shared_buffers"].meets_recommendation is False
    # work_mem: 4MB < 16MB -> not met
    assert result["work_mem"].meets_recommendation is False
    # effective_cache_size: 1GB < 2GB -> not met
    assert result["effective_cache_size"].meets_recommendation is False


def test_assess_config_all_met():
    """assess_config returns all met when current >= recommended."""
    current_config = {
        "shared_buffers": "512MB",
        "work_mem": "32MB",
    }
    recommendations = {
        "shared_buffers": "256MB",
        "work_mem": "16MB",
    }
    result = assess_config(current_config, recommendations)
    assert all(ca.meets_recommendation for ca in result.values())


def test_compute_suitability_verdict_pass():
    """compute_suitability_verdict returns PASS when config met and latency low."""
    result = compute_suitability_verdict(
        config_met=True,
        avg_latency_ms=Decimal(10),
        max_latency_ms=Decimal(20),
    )
    assert result == SuitabilityVerdict.PASS


def test_compute_suitability_verdict_warn():
    """compute_suitability_verdict returns WARN when config not met but latency ok."""
    result = compute_suitability_verdict(
        config_met=False,
        avg_latency_ms=Decimal(10),
        max_latency_ms=Decimal(20),
    )
    assert result == SuitabilityVerdict.WARN


def test_compute_suitability_verdict_block_high_latency():
    """compute_suitability_verdict returns BLOCK when latency too high."""
    result = compute_suitability_verdict(
        config_met=True,
        avg_latency_ms=Decimal(200),
        max_latency_ms=Decimal(500),
    )
    assert result == SuitabilityVerdict.BLOCK


def test_run_postgres_benchmark():
    """run_postgres_benchmark returns BenchmarkResult with all fields."""
    result = run_postgres_benchmark(
        host="localhost",
        port=5432,
        dbname="superbot",
        user="superbot",
        password="secret",
        connect_timeout=1,
    )
    assert isinstance(result, BenchmarkResult)
    assert result.connection_ok is False  # no real PG running
    assert result.suitability in (
        SuitabilityVerdict.PASS,
        SuitabilityVerdict.WARN,
        SuitabilityVerdict.BLOCK,
    )


def test_benchmark_result_creates():
    """BenchmarkResult can be created."""
    br = BenchmarkResult(
        connection_ok=True,
        query_count=5,
        iterations=3,
        avg_latency_ms=Decimal("5.5"),
        max_latency_ms=Decimal("12.0"),
        min_latency_ms=Decimal("2.0"),
        config_met=True,
        suitability=SuitabilityVerdict.PASS,
    )
    assert br.connection_ok is True
    assert br.suitability == SuitabilityVerdict.PASS


def test_postgres_benchmark_deterministic():
    """Same inputs yield identical benchmark results."""
    PostgreSQLBenchmarkService()
    PostgreSQLBenchmarkService()
    # benchmark_queries is deterministic given same queries/iterations
    r1 = benchmark_queries(["SELECT 1"], iterations=2)
    r2 = benchmark_queries(["SELECT 1"], iterations=2)
    assert r1.avg_latency_ms == r2.avg_latency_ms
    assert r1.query_count == r2.query_count


def test_missing_connection_params_block():
    """Missing required connection params block rather than defaulting."""
    with pytest.raises(MissingInputError):
        PostgreSQLBenchmarkService(
            host=None,
            port=5432,
            dbname="superbot",
            user="superbot",
            password="secret",
        )


def test_suitability_verdict_creates():
    """SuitabilityVerdict enum values exist."""
    assert SuitabilityVerdict.PASS.value == "PASS"
    assert SuitabilityVerdict.WARN.value == "WARN"
    assert SuitabilityVerdict.BLOCK.value == "BLOCK"
