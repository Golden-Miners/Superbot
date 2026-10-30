"""M10.2 — Resource telemetry for API/workers/DB/model/MT5/data/queue.

Deterministic resource telemetry service:
- ResourceType: API, WORKER, DB, MODEL, MT5, DATA, QUEUE
- ResourceMetric: name, value, unit, timestamp, resource_type, resource_id
- ResourceSnapshot: point-in-time telemetry for a resource
- ResourceRegistry: register resources, record metrics, retrieve snapshots
- ResourceTelemetryCollector: collect metrics from resources
- ResourcePressure: detects when a resource is under pressure (high utilization)
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ResourceType(str, Enum):
    """Resource categories tracked by telemetry."""

    API = "api"
    WORKER = "worker"
    DB = "db"
    MODEL = "model"
    MT5 = "mt5"
    DATA = "data"
    QUEUE = "queue"


@dataclass(frozen=True)
class ResourceMetric:
    """A single telemetry metric reading."""

    name: str
    value: float
    unit: str
    timestamp: datetime
    resource_type: ResourceType
    resource_id: str


@dataclass(frozen=True)
class ResourceSnapshot:
    """Latest telemetry snapshot for a resource."""

    resource_id: str
    resource_type: ResourceType
    metrics: dict[str, float]
    timestamp: datetime


@dataclass(frozen=True)
class ResourceInfo:
    """Registered resource information."""

    resource_id: str
    resource_type: ResourceType
    endpoint: str


@dataclass(frozen=True)
class CollectorResult:
    """Result of a collection operation."""

    recorded: bool
    resource_id: str
    metric_name: str
    registered: bool = False


@dataclass(frozen=True)
class PressureResult:
    """Result of a pressure evaluation."""

    under_pressure: bool
    reasons: list[str]


class ResourceRegistry:
    """Registry of resources and their metric histories."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceInfo] = {}
        self._metrics: dict[str, dict[str, list[ResourceMetric]]] = {}

    def register_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        endpoint: str,
    ) -> None:
        """Register a resource for telemetry tracking."""
        self._resources[resource_id] = ResourceInfo(
            resource_id=resource_id,
            resource_type=resource_type,
            endpoint=endpoint,
        )
        self._metrics.setdefault(resource_id, {})

    def get_resource(self, resource_id: str) -> ResourceInfo | None:
        """Get registered resource info by ID."""
        return self._resources.get(resource_id)

    def list_resource_ids(self, resource_type: ResourceType | None = None) -> list[str]:
        """List all registered resource IDs, optionally filtered by type."""
        if resource_type is None:
            return list(self._resources.keys())
        return [rid for rid, info in self._resources.items() if info.resource_type == resource_type]

    def record_metric(self, metric: ResourceMetric) -> None:
        """Record a metric reading for a resource."""
        if metric.resource_id not in self._metrics:
            self._metrics[metric.resource_id] = {}
        self._metrics[metric.resource_id].setdefault(metric.name, []).append(metric)

    def get_metric_history(self, resource_id: str, metric_name: str) -> list[ResourceMetric]:
        """Get the history of a metric for a resource."""
        return self._metrics.get(resource_id, {}).get(metric_name, [])

    def get_snapshot(self, resource_id: str) -> ResourceSnapshot | None:
        """Get the latest snapshot for a resource."""
        info = self._resources.get(resource_id)
        if info is None:
            return None
        histories = self._metrics.get(resource_id, {})
        metrics: dict[str, float] = {}
        latest: datetime | None = None
        for name, history in histories.items():
            if not history:
                continue
            latest_metric = max(history, key=lambda m: m.timestamp)
            metrics[name] = latest_metric.value
            if latest is None or latest_metric.timestamp > latest:
                latest = latest_metric.timestamp
        if latest is None:
            latest = datetime.now()
        return ResourceSnapshot(
            resource_id=resource_id,
            resource_type=info.resource_type,
            metrics=metrics,
            timestamp=latest,
        )


class ResourcePressure:
    """Detects when a resource is under pressure based on utilization thresholds."""

    def __init__(
        self,
        cpu_threshold: float = 0.8,
        memory_threshold: float = 0.85,
    ) -> None:
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

    def evaluate(self, metrics: dict[str, float]) -> PressureResult:
        """Evaluate whether metrics indicate resource pressure."""
        reasons: list[str] = []

        cpu = metrics.get("cpu_usage")
        if cpu is not None and cpu > self.cpu_threshold:
            reasons.append(f"cpu_usage {cpu} above threshold {self.cpu_threshold}")

        memory_used = metrics.get("memory_mb")
        memory_total = metrics.get("memory_total_mb")
        if memory_used is not None and memory_total is not None and memory_total > 0:
            memory_ratio = memory_used / memory_total
            if memory_ratio > self.memory_threshold:
                reasons.append(
                    f"memory_usage {memory_ratio:.2f} above threshold {self.memory_threshold}"
                )

        return PressureResult(under_pressure=len(reasons) > 0, reasons=reasons)


class ResourceTelemetryCollector:
    """Collects telemetry metrics into a resource registry."""

    def __init__(self, registry: ResourceRegistry | None = None) -> None:
        self.registry = registry

    def collect(
        self,
        resource_id: str,
        name: str,
        value: float,
        unit: str,
        timestamp: datetime | None = None,
    ) -> CollectorResult:
        """Collect a metric for a resource."""
        info = self.registry.get_resource(resource_id)
        if info is None:
            return CollectorResult(recorded=False, resource_id=resource_id, metric_name=name)
        metric = ResourceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=timestamp if timestamp is not None else datetime.now(),
            resource_type=info.resource_type,
            resource_id=resource_id,
        )
        self.registry.record_metric(metric)
        return CollectorResult(recorded=True, resource_id=resource_id, metric_name=name)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def register_resource(
    registry: ResourceRegistry,
    resource_id: str,
    resource_type: ResourceType,
    endpoint: str,
) -> CollectorResult:
    """Convenience: register a resource."""
    registry.register_resource(resource_id, resource_type, endpoint)
    return CollectorResult(recorded=True, resource_id=resource_id, metric_name="", registered=True)


def record_metric(
    registry: ResourceRegistry,
    resource_id: str,
    name: str,
    value: float,
    unit: str,
    timestamp: datetime | None = None,
) -> CollectorResult:
    """Convenience: record a metric."""
    info = registry.get_resource(resource_id)
    if info is None:
        return CollectorResult(recorded=False, resource_id=resource_id, metric_name=name)
    metric = ResourceMetric(
        name=name,
        value=value,
        unit=unit,
        timestamp=timestamp if timestamp is not None else datetime.now(),
        resource_type=info.resource_type,
        resource_id=resource_id,
    )
    registry.record_metric(metric)
    return CollectorResult(recorded=True, resource_id=resource_id, metric_name=name)


def collect_metric(
    registry: ResourceRegistry,
    resource_id: str,
    name: str,
    value: float,
    unit: str,
    timestamp: datetime | None = None,
) -> CollectorResult:
    """Convenience: collect a metric via ResourceTelemetryCollector."""
    collector = ResourceTelemetryCollector(registry)
    return collector.collect(resource_id, name, value, unit, timestamp)


def get_snapshot(registry: ResourceRegistry, resource_id: str) -> ResourceSnapshot | None:
    """Convenience: get the latest snapshot for a resource."""
    return registry.get_snapshot(resource_id)


def get_resource_pressure(
    metrics: dict[str, float],
    cpu_threshold: float = 0.8,
    memory_threshold: float = 0.85,
) -> PressureResult:
    """Convenience: evaluate pressure for metrics."""
    return ResourcePressure(
        cpu_threshold=cpu_threshold,
        memory_threshold=memory_threshold,
    ).evaluate(metrics)
