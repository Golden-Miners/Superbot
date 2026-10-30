"""RED tests for M10.2 — Resource telemetry for API/workers/DB/model/MT5/data/queue.

Tests define:
- ResourceType: API, WORKER, DB, MODEL, MT5, DATA, QUEUE
- ResourceMetric: name, value, unit, timestamp, resource_type, resource_id
- ResourceSnapshot: point-in-time telemetry for a resource
- ResourceRegistry: register resources, record metrics, retrieve snapshots
- TelemetryCollector: collect metrics from resources, compute aggregates
- ResourcePressure: detects when a resource is under pressure (high utilization)
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from datetime import datetime

from superbot.m10.resource_telemetry import (
    ResourceMetric,
    ResourcePressure,
    ResourceRegistry,
    ResourceSnapshot,
    ResourceTelemetryCollector,
    ResourceType,
    collect_metric,
    get_resource_pressure,
    get_snapshot,
    record_metric,
    register_resource,
)


def test_resource_type_enum():
    """ResourceType defines all required resource categories."""
    assert ResourceType.API.value == "api"
    assert ResourceType.WORKER.value == "worker"
    assert ResourceType.DB.value == "db"
    assert ResourceType.MODEL.value == "model"
    assert ResourceType.MT5.value == "mt5"
    assert ResourceType.DATA.value == "data"
    assert ResourceType.QUEUE.value == "queue"


def test_resource_metric_creates():
    """ResourceMetric stores name, value, unit, timestamp, resource_type, resource_id."""
    metric = ResourceMetric(
        name="cpu_usage",
        value=0.65,
        unit="percent",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        resource_type=ResourceType.API,
        resource_id="api_1",
    )
    assert metric.name == "cpu_usage"
    assert metric.value == 0.65
    assert metric.unit == "percent"
    assert metric.resource_type == ResourceType.API
    assert metric.resource_id == "api_1"


def test_resource_snapshot_creates():
    """ResourceSnapshot stores resource id, type, metrics, timestamp."""
    snapshot = ResourceSnapshot(
        resource_id="db_1",
        resource_type=ResourceType.DB,
        metrics={"cpu_usage": 0.4, "memory_mb": 2048},
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    assert snapshot.resource_id == "db_1"
    assert snapshot.resource_type == ResourceType.DB
    assert snapshot.metrics == {"cpu_usage": 0.4, "memory_mb": 2048}


def test_resource_registry_creates():
    """ResourceRegistry can be created."""
    registry = ResourceRegistry()
    assert registry is not None


def test_register_resource():
    """register_resource adds a resource to the registry."""
    registry = ResourceRegistry()
    registry.register_resource("api_1", ResourceType.API, "http://localhost:8000")
    info = registry.get_resource("api_1")
    assert info is not None
    assert info.resource_id == "api_1"
    assert info.resource_type == ResourceType.API


def test_get_unknown_resource():
    """get_resource returns None for unknown resource."""
    registry = ResourceRegistry()
    assert registry.get_resource("nonexistent") is None


def test_record_metric():
    """record_metric adds a metric to a resource's history."""
    registry = ResourceRegistry()
    registry.register_resource("worker_1", ResourceType.WORKER, "worker-1")
    metric = ResourceMetric(
        name="jobs_processed",
        value=150,
        unit="count",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        resource_type=ResourceType.WORKER,
        resource_id="worker_1",
    )
    registry.record_metric(metric)
    history = registry.get_metric_history("worker_1", "jobs_processed")
    assert len(history) == 1
    assert history[0].value == 150


def test_get_snapshot():
    """get_snapshot returns the latest snapshot for a resource."""
    registry = ResourceRegistry()
    registry.register_resource("db_1", ResourceType.DB, "db-primary")
    m1 = ResourceMetric(
        name="cpu_usage",
        value=0.3,
        unit="percent",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        resource_type=ResourceType.DB,
        resource_id="db_1",
    )
    m2 = ResourceMetric(
        name="cpu_usage",
        value=0.7,
        unit="percent",
        timestamp=datetime(2026, 10, 28, 9, 5, 0),
        resource_type=ResourceType.DB,
        resource_id="db_1",
    )
    registry.record_metric(m1)
    registry.record_metric(m2)
    snapshot = registry.get_snapshot("db_1")
    assert snapshot is not None
    assert snapshot.metrics["cpu_usage"] == 0.7


def test_telemetry_collector_creates():
    """ResourceTelemetryCollector can be created."""
    collector = ResourceTelemetryCollector()
    assert collector is not None


def test_collect_metric_api():
    """collect_metric records an API resource metric."""
    registry = ResourceRegistry()
    registry.register_resource("api_1", ResourceType.API, "http://localhost:8000")
    result = collect_metric(
        registry,
        "api_1",
        "request_latency_ms",
        120.5,
        "ms",
    )
    assert result.recorded is True
    history = registry.get_metric_history("api_1", "request_latency_ms")
    assert len(history) == 1
    assert history[0].value == 120.5


def test_collect_metric_unknown_resource():
    """collect_metric on unknown resource returns recorded=False."""
    registry = ResourceRegistry()
    result = collect_metric(
        registry,
        "nonexistent",
        "cpu_usage",
        0.5,
        "percent",
    )
    assert result.recorded is False


def test_resource_pressure_detects():
    """ResourcePressure detects when utilization exceeds threshold."""
    pressure = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    result = pressure.evaluate({"cpu_usage": 0.9, "memory_mb": 9000, "memory_total_mb": 10000})
    assert result.under_pressure is True
    assert any("cpu" in r.lower() for r in result.reasons)


def test_resource_pressure_no_pressure():
    """ResourcePressure reports no pressure when utilization below thresholds."""
    pressure = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    result = pressure.evaluate({"cpu_usage": 0.4, "memory_mb": 4000, "memory_total_mb": 10000})
    assert result.under_pressure is False
    assert result.reasons == []


def test_resource_pressure_memory():
    """ResourcePressure detects memory pressure."""
    pressure = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    result = pressure.evaluate({"cpu_usage": 0.3, "memory_mb": 9500, "memory_total_mb": 10000})
    assert result.under_pressure is True
    assert any("memory" in r.lower() for r in result.reasons)


def test_resource_pressure_deterministic():
    """Same metrics yield identical pressure result."""
    p1 = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    p2 = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    metrics = {"cpu_usage": 0.9, "memory_mb": 9000, "memory_total_mb": 10000}
    r1 = p1.evaluate(metrics)
    r2 = p2.evaluate(metrics)
    assert r1.under_pressure == r2.under_pressure
    assert r1.reasons == r2.reasons


def test_get_resource_pressure_function():
    """get_resource_pressure convenience function works."""
    result = get_resource_pressure({"cpu_usage": 0.9}, cpu_threshold=0.8)
    assert result.under_pressure is True


def test_get_snapshot_function():
    """get_snapshot convenience function works."""
    registry = ResourceRegistry()
    registry.register_resource("q_1", ResourceType.QUEUE, "queue-main")
    m = ResourceMetric(
        name="depth",
        value=25,
        unit="count",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        resource_type=ResourceType.QUEUE,
        resource_id="q_1",
    )
    registry.record_metric(m)
    snapshot = get_snapshot(registry, "q_1")
    assert snapshot is not None
    assert snapshot.metrics["depth"] == 25


def test_register_resource_function():
    """register_resource convenience function works."""
    registry = ResourceRegistry()
    result = register_resource(registry, "mt5_1", ResourceType.MT5, "mt5-terminal-1")
    assert result.registered is True
    assert registry.get_resource("mt5_1") is not None


def test_record_metric_function():
    """record_metric convenience function works."""
    registry = ResourceRegistry()
    registry.register_resource("model_1", ResourceType.MODEL, "model-v1")
    result = record_metric(
        registry,
        "model_1",
        "inference_latency_ms",
        45.2,
        "ms",
    )
    assert result.recorded is True


def test_collect_metric_function():
    """collect_metric convenience function works."""
    registry = ResourceRegistry()
    registry.register_resource("data_1", ResourceType.DATA, "data-feed-1")
    result = collect_metric(registry, "data_1", "rows_per_second", 10000, "rows/sec")
    assert result.recorded is True


def test_registry_lists_resources():
    """registry lists all registered resource IDs."""
    registry = ResourceRegistry()
    registry.register_resource("r1", ResourceType.API, "a")
    registry.register_resource("r2", ResourceType.DB, "b")
    registry.register_resource("r3", ResourceType.QUEUE, "c")
    ids = registry.list_resource_ids()
    assert set(ids) == {"r1", "r2", "r3"}


def test_registry_resources_by_type():
    """registry lists resource IDs filtered by type."""
    registry = ResourceRegistry()
    registry.register_resource("api1", ResourceType.API, "a")
    registry.register_resource("db1", ResourceType.DB, "b")
    registry.register_resource("api2", ResourceType.API, "c")
    apis = registry.list_resource_ids(ResourceType.API)
    assert set(apis) == {"api1", "api2"}


def test_snapshot_deterministic():
    """Same metrics yield identical snapshot."""
    r1 = ResourceRegistry()
    r1.register_resource("x", ResourceType.DATA, "d")
    r1.record_metric(
        ResourceMetric(
            "rows", 1000, "count", datetime(2026, 10, 28, 9, 0, 0), ResourceType.DATA, "x"
        )
    )
    r2 = ResourceRegistry()
    r2.register_resource("x", ResourceType.DATA, "d")
    r2.record_metric(
        ResourceMetric(
            "rows", 1000, "count", datetime(2026, 10, 28, 9, 0, 0), ResourceType.DATA, "x"
        )
    )
    s1 = r1.get_snapshot("x")
    s2 = r2.get_snapshot("x")
    assert s1.metrics == s2.metrics
    assert s1.timestamp == s2.timestamp


def test_pressure_without_memory_total():
    """ResourcePressure handles missing memory_total_mb gracefully."""
    pressure = ResourcePressure(cpu_threshold=0.8, memory_threshold=0.85)
    result = pressure.evaluate({"cpu_usage": 0.5, "memory_mb": 4000})
    assert result.under_pressure is False
