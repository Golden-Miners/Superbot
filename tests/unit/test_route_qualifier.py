"""RED tests for M9.2 — Qualify task/model routes on quality, schema, repeatability, latency, memory.

Tests define:
- RouteSpec: route configuration (model, task type, thresholds)
- RouteResult: qualification result (qualified/blocked, metrics, reasons)
- RouteQualifier: evaluates routes against quality, schema, repeatability, latency, memory thresholds
- Quality threshold: quality_score >= min_quality
- Schema threshold: schema_valid == True
- Repeatability threshold: repeated runs produce identical results
- Latency threshold: avg_latency_ms <= max_latency_ms
- Memory threshold: avg_memory_mb <= max_memory_mb
- Missing/unavailable model blocks
- Deterministic: same inputs → identical results
- Stdlib-only, no import-time network activity
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.m9.route_qualifier import (
    ModelRoute,
    RouteQualifier,
    RouteSpec,
    qualify_route,
)


def test_route_spec_creates():
    """RouteSpec can be created with all thresholds."""
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    assert spec.model == "llama3"
    assert spec.task_type == "summarize"
    assert spec.min_quality == Decimal("0.8")
    assert spec.max_latency_ms == Decimal(500)
    assert spec.max_memory_mb == Decimal(4096)
    assert spec.require_schema is True
    assert spec.min_repeatability == Decimal("0.95")


def test_route_qualifier_creates():
    """RouteQualifier can be created."""
    q = RouteQualifier()
    assert q is not None


def test_qualify_route_pass():
    """qualify_route returns PASS when all thresholds met."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is True
    assert result.reasons == []


def test_qualify_route_fail_quality():
    """qualify_route fails when quality below threshold."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.5"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is False
    assert any("quality" in r.lower() for r in result.reasons)


def test_qualify_route_fail_latency():
    """qualify_route fails when latency above max."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(600),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is False
    assert any("latency" in r.lower() for r in result.reasons)


def test_qualify_route_fail_memory():
    """qualify_route fails when memory above max."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(8000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is False
    assert any("memory" in r.lower() or "memory_mb" in r.lower() for r in result.reasons)


def test_qualify_route_fail_schema():
    """qualify_route fails when schema invalid."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=False,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is False
    assert any("schema" in r.lower() for r in result.reasons)


def test_qualify_route_fail_repeatability():
    """qualify_route fails when repeatability below min."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.5"),
    )
    assert result.qualified is False
    assert any("repeatability" in r.lower() for r in result.reasons)


def test_qualify_route_multiple_failures():
    """qualify_route reports all failing criteria."""
    q = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    result = qualify_route(
        q,
        spec,
        quality_score=Decimal("0.5"),
        latency_ms=Decimal(600),
        memory_mb=Decimal(8000),
        schema_valid=False,
        repeatability=Decimal("0.5"),
    )
    assert result.qualified is False
    assert len(result.reasons) >= 4


def test_route_qualifier_deterministic():
    """Same inputs yield identical results."""
    q1 = RouteQualifier()
    q2 = RouteQualifier()
    spec = RouteSpec(
        model="llama3",
        task_type="summarize",
        min_quality=Decimal("0.8"),
        max_latency_ms=Decimal(500),
        max_memory_mb=Decimal(4096),
        require_schema=True,
        min_repeatability=Decimal("0.95"),
    )
    r1 = qualify_route(
        q1,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    r2 = qualify_route(
        q2,
        spec,
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert r1.qualified == r2.qualified
    assert r1.reasons == r2.reasons


def test_model_route_creates():
    """ModelRoute can be created."""
    mr = ModelRoute(model_id="llama3", endpoint="http://localhost:11434", task_type="summarize")
    assert mr.model_id == "llama3"
    assert mr.endpoint == "http://localhost:11434"
    assert mr.task_type == "summarize"


def test_register_route():
    """register_route adds a route to the qualifier."""
    q = RouteQualifier()
    mr = ModelRoute(model_id="llama3", endpoint="http://localhost:11434", task_type="summarize")
    q.register_route(mr)
    assert q.get_route("llama3") == mr


def test_qualify_route_by_model_id():
    """qualify_route looks up route by model_id."""
    q = RouteQualifier()
    q.register_route(
        ModelRoute(model_id="llama3", endpoint="http://localhost:11434", task_type="summarize")
    )
    result = q.qualify_model(
        "llama3",
        quality_score=Decimal("0.9"),
        latency_ms=Decimal(100),
        memory_mb=Decimal(1000),
        schema_valid=True,
        repeatability=Decimal("0.98"),
    )
    assert result.qualified is True


def test_qualify_route_unknown_model():
    """qualify_route raises for unknown model."""
    q = RouteQualifier()
    with pytest.raises(KeyError):
        q.qualify_model(
            "nonexistent",
            quality_score=Decimal("0.9"),
            latency_ms=Decimal(100),
            memory_mb=Decimal(1000),
            schema_valid=True,
            repeatability=Decimal("0.98"),
        )
