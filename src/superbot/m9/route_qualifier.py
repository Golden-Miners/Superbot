"""M9.2 — Qualify task/model routes on quality, schema, repeatability, latency, memory.

Deterministic route qualification service:
- RouteSpec: route configuration (model, task type, thresholds)
- RouteQualifier: evaluates routes against quality, schema, repeatability, latency, memory thresholds
- RouteResult / QualifyResult: qualification result (qualified/blocked, metrics, reasons)
- ModelRoute: model registration with endpoint
- Missing/unavailable model blocks (raises KeyError), never passes
- Stdlib-only; no import-time network activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RouteSpec:
    """Route configuration with quality, schema, repeatability, latency, memory thresholds."""

    model: str
    task_type: str
    min_quality: Decimal
    max_latency_ms: Decimal
    max_memory_mb: Decimal
    require_schema: bool
    min_repeatability: Decimal


@dataclass(frozen=True)
class RouteResult:
    """Route qualification result."""

    model: str
    task_type: str
    qualified: bool
    quality_score: Decimal
    latency_ms: Decimal
    memory_mb: Decimal
    schema_valid: bool
    repeatability: Decimal
    reasons: list[str]


@dataclass(frozen=True)
class ModelRoute:
    """Model route registration."""

    model_id: str
    endpoint: str
    task_type: str


class RouteQualifier:
    """Evaluates route qualification against config thresholds."""

    def __init__(self) -> None:
        self._routes: dict[str, ModelRoute] = {}

    def register_route(self, route: ModelRoute) -> None:
        """Register a model route."""
        self._routes[route.model_id] = route

    def get_route(self, model_id: str) -> ModelRoute | None:
        """Get a registered route by model id."""
        return self._routes.get(model_id)

    def qualify_route(
        self,
        spec: RouteSpec,
        quality_score: Decimal,
        latency_ms: Decimal,
        memory_mb: Decimal,
        schema_valid: bool,
        repeatability: Decimal,
    ) -> RouteResult:
        """Evaluate route qualification against spec thresholds.

        Args:
            spec: RouteSpec with thresholds
            quality_score: quality score (0-1)
            latency_ms: latency in milliseconds
            memory_mb: memory in MB
            schema_valid: whether schema validation passed
            repeatability: repeatability score (0-1)

        Returns RouteResult with qualified flag and failure reasons.
        """
        reasons: list[str] = []
        qualified = True

        if quality_score < spec.min_quality:
            reasons.append(f"quality_score {quality_score} below min {spec.min_quality}")
            qualified = False

        if latency_ms > spec.max_latency_ms:
            reasons.append(f"latency_ms {latency_ms} above max {spec.max_latency_ms}")
            qualified = False

        if memory_mb > spec.max_memory_mb:
            reasons.append(f"memory_mb {memory_mb} above max {spec.max_memory_mb}")
            qualified = False

        if spec.require_schema and not schema_valid:
            reasons.append(f"schema_valid {schema_valid} below required {spec.require_schema}")
            qualified = False

        if repeatability < spec.min_repeatability:
            reasons.append(f"repeatability {repeatability} below min {spec.min_repeatability}")
            qualified = False

        return RouteResult(
            model=spec.model,
            task_type=spec.task_type,
            qualified=qualified,
            quality_score=quality_score,
            latency_ms=latency_ms,
            memory_mb=memory_mb,
            schema_valid=schema_valid,
            repeatability=repeatability,
            reasons=reasons,
        )

    def qualify_model(
        self,
        model_id: str,
        quality_score: Decimal,
        latency_ms: Decimal,
        memory_mb: Decimal,
        schema_valid: bool,
        repeatability: Decimal,
    ) -> RouteResult:
        """Qualify a route by model_id using the qualifier's registered spec."""
        route = self.get_route(model_id)
        if route is None:
            raise KeyError(f"Model route {model_id} not registered")
        return self.qualify_route(
            spec=RouteSpec(
                model=route.model_id,
                task_type=route.task_type,
                min_quality=Decimal("0.8"),
                max_latency_ms=Decimal(500),
                max_memory_mb=Decimal(4096),
                require_schema=True,
                min_repeatability=Decimal("0.95"),
            ),
            quality_score=quality_score,
            latency_ms=latency_ms,
            memory_mb=memory_mb,
            schema_valid=schema_valid,
            repeatability=repeatability,
        )


def qualify_route(
    evaluator: RouteQualifier,
    spec: RouteSpec,
    quality_score: Decimal,
    latency_ms: Decimal,
    memory_mb: Decimal,
    schema_valid: bool,
    repeatability: Decimal,
) -> RouteResult:
    """Evaluate route qualification against spec thresholds (convenience function)."""
    return evaluator.qualify_route(
        spec=spec,
        quality_score=quality_score,
        latency_ms=latency_ms,
        memory_mb=memory_mb,
        schema_valid=schema_valid,
        repeatability=repeatability,
    )


def qualify_route_registry(
    qualifier: RouteQualifier,
    model_id: str,
    quality_score: Decimal,
    latency_ms: Decimal,
    memory_mb: Decimal,
    schema_valid: bool,
    repeatability: Decimal,
) -> RouteResult:
    """Qualify a route by model_id using the qualifier's registered spec."""
    route = qualifier.get_route(model_id)
    if route is None:
        raise KeyError(f"Model route {model_id} not registered")
    return qualifier.qualify_route(
        spec=RouteSpec(
            model=route.model_id,
            task_type=route.task_type,
            min_quality=Decimal("0.8"),
            max_latency_ms=Decimal(500),
            max_memory_mb=Decimal(4096),
            require_schema=True,
            min_repeatability=Decimal("0.95"),
        ),
        quality_score=quality_score,
        latency_ms=latency_ms,
        memory_mb=memory_mb,
        schema_valid=schema_valid,
        repeatability=repeatability,
    )


def register_route(
    qualifier: RouteQualifier,
    model_id: str,
    endpoint: str,
    task_type: str,
) -> None:
    """Register a route (convenience function)."""
    qualifier.register_route(ModelRoute(model_id=model_id, endpoint=endpoint, task_type=task_type))


# QualifyResult is an alias for RouteResult, kept for API compatibility.
QualifyResult = RouteResult
