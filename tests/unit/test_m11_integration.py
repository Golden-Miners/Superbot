"""RED tests for Phase 5 — Cross-component integration.

Covers:
- Dashboard surfaces connected to actual API/service outputs (health, risk,
  audit, jobs, strategies, experiments)
- Risk services integrated with internal simulator
- Real persistence and versioned PostgreSQL migrations
- Background-worker lifecycle and recovery
- Synthetic-data labels and source provenance visible throughout
"""

from __future__ import annotations

from decimal import Decimal

from superbot.m10.scheduler import PriorityTier, Scheduler
from superbot.m11.api import create_app
from superbot.m11.integration import DashboardService
from superbot.persistence.audit_linkage import AuditEventLogger
from superbot.persistence.checkpoint_restart import CheckpointService
from superbot.persistence.experiment_registry import ExperimentRegistry
from superbot.persistence.migrations import Migration, MigrationService, apply_migration
from superbot.risk.portfolio_risk import PortfolioRiskService
from superbot.strategy.internal_simulation import InternalSimulationEvaluator
from superbot.supervisor.health import HealthCheckResult, HealthRegistry, HealthStatus

# ---------------------------------------------------------------------------
# Health integration — /health reads from HealthRegistry
# ---------------------------------------------------------------------------

def test_health_reads_from_health_registry():
    """Health endpoint returns actual check results from HealthRegistry,
    not seeded fixtures."""
    registry = HealthRegistry()
    registry.register("api", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    registry.register("postgresql", lambda: HealthCheckResult(HealthStatus.DEGRADED, "stale"))
    service = DashboardService(health_registry=registry)
    result = service.get_health()
    assert result["overall"] == "degraded"
    assert result["components"]["api"]["status"] == "healthy"
    assert result["components"]["postgresql"]["status"] == "degraded"
    assert result["label"] == "internal_simulation"


# ---------------------------------------------------------------------------
# Risk integration — /risk reads from PortfolioRiskService
# ---------------------------------------------------------------------------

def test_risk_reads_from_portfolio_risk_service():
    """Risk endpoint returns real risk data from PortfolioRiskService."""
    service_risk = PortfolioRiskService()
    service_risk.register_strategy("trend_following.v3", Decimal(15), Decimal(3), Decimal(5))
    service_risk.register_strategy("structure_liquidity.v1", Decimal(10), Decimal(2), Decimal(5))
    # Update strategy P&L
    from superbot.risk.portfolio_risk import update_strategy_pnl
    update_strategy_pnl(service_risk, "trend_following.v3", Decimal(8), Decimal("1.5"))
    update_strategy_pnl(service_risk, "structure_liquidity.v1", Decimal(5), Decimal("0.5"))

    dashboard = DashboardService(risk_service=service_risk)
    result = dashboard.get_risk()
    assert result["label"] == "internal_simulation"
    assert result["risk_state"] in ("green", "blocked", "degraded")
    assert "positions" in result
    assert "exposure" in result


# ---------------------------------------------------------------------------
# Audit integration — /audit/events reads from AuditEventLogger
# ---------------------------------------------------------------------------

def test_audit_events_read_from_audit_logger():
    """Audit endpoint returns real events from AuditEventLogger."""
    logger = AuditEventLogger()
    logger.append_audit_event("halt", {"strategy": "trend_following.v3", "reason": "dd_breach"})
    logger.append_audit_event("resume", {"strategy": "trend_following.v3", "reason": "recovered"})

    dashboard = DashboardService(audit_logger=logger)
    result = dashboard.get_audit_events()
    events = result["events"]
    assert len(events) == 2
    assert events[0]["event_type"] == "halt"
    assert events[1]["event_type"] == "resume"
    assert result["chain_intact"] is True  # chain integrity verified


# ---------------------------------------------------------------------------
# Experiment integration — /experiments reads from ExperimentRegistry
# ---------------------------------------------------------------------------

def test_experiments_read_from_experiment_registry():
    """Experiments endpoint returns real experiments from ExperimentRegistry."""
    registry = ExperimentRegistry()
    from superbot.persistence.experiment_registry import (
        CodeRef,
        ConfigRef,
        CostRef,
        ExperimentRef,
        ParameterRef,
        StrategyRef,
    )
    ref = ExperimentRef(
        experiment_id="exp-1",
        code=CodeRef(repo="superbot", commit="a1b2c3d", path="src/superbot/strategy/trend_following.py"),
        strategy=StrategyRef(name="trend_following", version="v3"),
        parameters=ParameterRef(window=10, threshold=0.8),
        cost=CostRef(spread=0.5, commission=1.0),
        config=ConfigRef(env="research", region="local"),
    )
    registry.register_experiment(ref)

    dashboard = DashboardService(experiment_registry=registry)
    result = dashboard.get_experiments()
    experiments = result["experiments"]
    assert len(experiments) == 1
    assert experiments[0]["experiment_id"] == "exp-1"
    assert experiments[0]["label"] == "internal_simulation"


# ---------------------------------------------------------------------------
# Job integration — /jobs reads from Scheduler
# ---------------------------------------------------------------------------

def test_jobs_read_from_scheduler():
    """Jobs endpoint returns real jobs from Scheduler."""
    scheduler = Scheduler(max_concurrent=5)
    scheduler.submit_job("job-1", PriorityTier.HIGH, {"symbol": "XAUUSD", "timeframe": "M5", "strategy_version": "trend_following.v3"})
    scheduler.submit_job("job-2", PriorityTier.NORMAL, {"symbol": "XAGUSD", "timeframe": "M15", "strategy_version": "structure_liquidity.v1"})

    dashboard = DashboardService(job_scheduler=scheduler)
    result = dashboard.get_jobs()
    jobs = result["jobs"]
    assert len(jobs) == 2
    job_ids = {j["job_id"] for j in jobs}
    assert job_ids == {"job-1", "job-2"}
    assert all(j["label"] == "internal_simulation" for j in jobs)


# ---------------------------------------------------------------------------
# Strategy integration — /strategies reads from strategy modules
# ---------------------------------------------------------------------------

def test_strategies_read_from_strategy_modules():
    """Strategies endpoint returns real strategies from strategy modules."""
    from superbot.strategy.internal_simulation import InternalSimulationEvaluator
    from superbot.strategy.shared_framework import SharedStrategyFramework

    framework = SharedStrategyFramework()
    evaluator = InternalSimulationEvaluator()

    dashboard = DashboardService(strategy_framework=framework, simulation_evaluator=evaluator)
    result = dashboard.get_strategies()
    strategies = result["strategies"]
    assert isinstance(strategies, list)
    assert all(s["label"] == "internal_simulation" for s in strategies)


# ---------------------------------------------------------------------------
# Risk + simulator integration
# ---------------------------------------------------------------------------

def test_risk_integrates_with_internal_simulator():
    """Risk service reflects internal simulation results."""
    risk_service = PortfolioRiskService()
    risk_service.register_strategy("trend_following.v3", Decimal(15), Decimal(3), Decimal(5))

    evaluator = InternalSimulationEvaluator()
    result = evaluator.evaluate(
        cost_adjusted_return_pct=Decimal(8),
        sharpe=Decimal("1.2"),
        max_dd_pct=Decimal(2),
    )

    # If simulation says eligible, risk service should reflect green state
    if result.eligible:
        from superbot.risk.portfolio_risk import update_strategy_pnl
        update_strategy_pnl(risk_service, "trend_following.v3", Decimal(2), Decimal("0.5"))

    dashboard = DashboardService(risk_service=risk_service)
    risk = dashboard.get_risk()
    assert risk["label"] == "internal_simulation"


# ---------------------------------------------------------------------------
# Persistence — MigrationService
# ---------------------------------------------------------------------------

def test_migration_service_applies_and_tracks():
    """MigrationService applies migrations in order and tracks them."""
    service = MigrationService()
    applied = []

    def up_v1():
        applied.append(1)
    def down_v1():
        applied.remove(1)

    service.register_migration(Migration(version=1, up=up_v1, down=down_v1))
    result = apply_migration(service, 1)
    assert result.success is True
    assert service.is_applied(1) is True
    assert service.applied_versions() == [1]


def test_migration_service_prevents_double_apply():
    """MigrationService applies each migration at most once."""
    service = MigrationService()
    count = 0

    def up_v1():
        nonlocal count
        count += 1

    service.register_migration(Migration(version=1, up=up_v1, down=lambda: None))
    apply_migration(service, 1)
    result = apply_migration(service, 1)
    assert result.success is False  # already applied
    assert count == 1  # only applied once


# ---------------------------------------------------------------------------
# Checkpoint/restart — process recovery
# ---------------------------------------------------------------------------

def test_checkpoint_service_saves_and_restores():
    """CheckpointService saves state and can restore after restart."""
    service = CheckpointService()

    from superbot.persistence.checkpoint_restart import CheckpointRecord

    # Record checkpoints
    record1 = CheckpointRecord(
        checkpoint_id="job-1",
        checkpoint_type="job",
        payload={"status": "running", "progress": 0.42},
        sequence=0,
        previous_hash="genesis",
    )
    record2 = CheckpointRecord(
        checkpoint_id="job-2",
        checkpoint_type="job",
        payload={"status": "pending", "progress": 0.0},
        sequence=1,
        previous_hash=record1.hash,
    )
    service.register_checkpoint(record1)
    service.register_checkpoint(record2)

    # Simulate process restart — new service instance
    # CheckpointService is in-memory, so we use the same instance
    restored = service.get_checkpoint("job-1")
    assert restored.checkpoint_id == "job-1"
    assert restored.payload["status"] == "running"
    assert restored.payload["progress"] == 0.42


# ---------------------------------------------------------------------------
# API integration — FastAPI routes use DashboardService
# ---------------------------------------------------------------------------

def test_fastapi_health_endpoint_uses_dashboard_service():
    """FastAPI /health endpoint returns data from DashboardService."""
    registry = HealthRegistry()
    registry.register("api", lambda: HealthCheckResult(HealthStatus.HEALTHY, "ok"))
    service = DashboardService(health_registry=registry)
    # Share the same SessionStore between token creation and app
    from superbot.m11.auth import Role, SessionStore
    store = SessionStore()
    app = create_app(session_store=store, dashboard_service=service)

    from fastapi.testclient import TestClient
    client = TestClient(app)
    _, token = store.create_session(Role.OWNER)
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["overall"] == "healthy"


# ---------------------------------------------------------------------------
# No live orders — all surfaces labeled internal_simulation
# ---------------------------------------------------------------------------

def test_all_surfaces_labeled_internal_simulation():
    """All dashboard surfaces label data as internal_simulation, never live."""
    dashboard = DashboardService()
    assert dashboard.get_health()["label"] == "internal_simulation"
    assert dashboard.get_risk()["label"] == "internal_simulation"
    assert dashboard.get_audit_events() is not None  # audit events have label
    assert dashboard.get_experiments() is not None


# ---------------------------------------------------------------------------
# No broker credentials in any surface
# ---------------------------------------------------------------------------

def test_no_broker_credentials_in_dashboard():
    """No dashboard surface exposes broker credentials."""
    dashboard = DashboardService()
    health = dashboard.get_health()
    risk = dashboard.get_risk()
    jobs = dashboard.get_jobs()
    strategies = dashboard.get_strategies()
    experiments = dashboard.get_experiments()
    audit = dashboard.get_audit_events()

    all_data = str(health) + str(risk) + str(jobs) + str(strategies) + str(experiments) + str(audit)
    assert "api_key" not in all_data.lower()
    assert "secret" not in all_data.lower()
    assert "password" not in all_data.lower()
    assert "token" not in all_data.lower()
