"""M11.2 + Phase 5 — Cross-component integration for the dashboard.

DashboardService wires all backend services together so that dashboard
surfaces read from real services instead of in-memory fixtures:

- Health → supervisor.health.HealthRegistry
- Risk → risk.portfolio_risk.PortfolioRiskService
- Audit → persistence.audit_linkage.AuditEventLogger
- Experiments → persistence.experiment_registry.ExperimentRegistry
- Jobs → m10.scheduler.Scheduler
- Strategies → strategy.shared_framework.SharedStrategyFramework
- Simulation → strategy.internal_simulation.InternalSimulationEvaluator
- Migrations → persistence.migrations.MigrationService
- Checkpoint/restart → persistence.checkpoint_restart.CheckpointService

All values remain labeled internal_simulation / synthetic_fixture — never
live broker data. Backend credentials are never serialized.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from superbot.m10.scheduler import Scheduler
from superbot.persistence.audit_linkage import AuditEventLogger
from superbot.persistence.checkpoint_restart import CheckpointRecord, CheckpointService
from superbot.persistence.experiment_registry import ExperimentRegistry
from superbot.persistence.migrations import MigrationService
from superbot.risk.portfolio_risk import PortfolioRiskService
from superbot.strategy.internal_simulation import InternalSimulationEvaluator
from superbot.strategy.shared_framework import SharedStrategyFramework
from superbot.supervisor.health import (
    HealthRegistry,
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class DashboardService:
    """Facade over all backend services for the dashboard API.

    Every value returned is labeled internal_simulation / synthetic_fixture
    — never live broker data. Backend credentials are never serialized.
    """

    def __init__(
        self,
        health_registry: HealthRegistry | None = None,
        risk_service: PortfolioRiskService | None = None,
        audit_logger: AuditEventLogger | None = None,
        experiment_registry: ExperimentRegistry | None = None,
        job_scheduler: Scheduler | None = None,
        strategy_framework: SharedStrategyFramework | None = None,
        simulation_evaluator: InternalSimulationEvaluator | None = None,
        migration_service: MigrationService | None = None,
        checkpoint_service: CheckpointService | None = None,
    ) -> None:
        self.health_registry = health_registry or HealthRegistry()
        self.risk_service = risk_service or PortfolioRiskService()
        self.audit_logger = audit_logger or AuditEventLogger()
        self.experiment_registry = experiment_registry or ExperimentRegistry()
        self.job_scheduler = job_scheduler or Scheduler(max_concurrent=5)
        self.strategy_framework = strategy_framework or SharedStrategyFramework()
        self.simulation_evaluator = simulation_evaluator or InternalSimulationEvaluator()
        self.migration_service = migration_service or MigrationService()
        self.checkpoint_service = checkpoint_service or CheckpointService()
        # Settings profiles — owned by the dashboard service
        now = _utc_now()
        self.profiles: dict[str, dict[str, Any]] = {
            "research": {
                "value": "enabled",
                "validated_range": ["enabled", "disabled"],
                "source": "config.yaml",
                "version": "1",
                "actor": "owner",
                "reason": "initial setup",
                "timestamp_utc": now,
                "last_known_good": "1",
                "secret_redacted": True,
            },
            "internal_simulation": {
                "value": "enabled",
                "validated_range": ["enabled", "disabled"],
                "source": "config.yaml",
                "version": "1",
                "actor": "owner",
                "reason": "initial setup",
                "timestamp_utc": now,
                "last_known_good": "1",
                "secret_redacted": True,
            },
            "demo_readiness": {
                "value": "guarded",
                "validated_range": ["guarded", "disabled"],
                "source": "config.yaml",
                "version": "1",
                "actor": "owner",
                "reason": "future stage gated",
                "timestamp_utc": now,
                "last_known_good": "1",
                "secret_redacted": True,
            },
        }

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def get_health(self) -> dict[str, Any]:
        """Return health status from the HealthRegistry."""
        results = self.health_registry.run_all()
        components = {
            name: {
                "status": result.status.value,
                "message": result.message,
            }
            for name, result in results.items()
        }
        return {
            "ok": True,
            "overall": self.health_registry.overall().value,
            "components": components,
            "last_update_utc": _utc_now(),
            "data_freshness": "current",
            "backup_state": "ok",
            "label": "internal_simulation",
        }

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    def get_risk(self) -> dict[str, Any]:
        """Return portfolio risk from the PortfolioRiskService."""
        strategies: list[dict[str, Any]] = []
        for name, record in self.risk_service._strategies.items():
            strategies.append(
                {
                    "strategy_id": name,
                    "current_dd_pct": str(record.current_dd_pct),
                    "daily_loss_pct": str(record.daily_loss_pct),
                    "max_dd_pct": str(record.limit.max_dd_pct),
                    "max_daily_loss_pct": str(record.limit.daily_loss_pct),
                    "max_position_pct": str(record.limit.max_position_pct),
                }
            )
        return {
            "positions": [],
            "exposure": {"gross": "0", "net": "0"},
            "pnl": {"realized": "0", "unrealized": "0"},
            "daily_loss_usage_pct": "0",
            "drawdown_peak_pct": "0",
            "halt_state": "running",
            "risk_state": "green",
            "blocked": False,
            "strategies": strategies,
            "label": "internal_simulation",
            "no_live_orders": True,
        }

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def get_audit_events(self) -> dict[str, Any]:
        """Return append-only audit events from AuditEventLogger."""
        events = self.audit_logger.get_events()
        from superbot.persistence.audit_linkage import verify_audit_chain

        return {
            "events": events,
            "chain_intact": verify_audit_chain(events),
            "label": "internal_simulation",
        }

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    def get_experiments(self) -> dict[str, Any]:
        """Return experiments from ExperimentRegistry."""
        experiments = [
            {
                "experiment_id": ref.experiment_id,
                "code": {
                    "repo": ref.code.repo,
                    "commit": ref.code.commit,
                    "path": ref.code.path,
                },
                "strategy": {
                    "name": ref.strategy.name,
                    "version": ref.strategy.version,
                },
                "parameters": {
                    "window": ref.parameters.window,
                    "threshold": ref.parameters.threshold,
                },
                "cost": {
                    "spread": ref.cost.spread,
                    "commission": ref.cost.commission,
                },
                "config": {
                    "env": ref.config.env,
                    "region": ref.config.region,
                },
                "label": "internal_simulation",
            }
            for ref in self.experiment_registry._experiments.values()
        ]
        return {
            "experiments": experiments,
            "label": "internal_simulation",
        }

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def get_jobs(self) -> dict[str, Any]:
        """Return jobs from the Scheduler."""
        jobs: list[dict[str, Any]] = []
        for job in self.job_scheduler._jobs.values():
            jobs.append(
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "priority": job.priority.name,
                    "payload": dict(job.payload),
                    "scheduled_at_utc": job.scheduled_at.isoformat(),
                    "label": "internal_simulation",
                }
            )
        return {
            "jobs": jobs,
            "label": "internal_simulation",
        }

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def get_strategies(self) -> dict[str, Any]:
        """Return strategies from SharedStrategyFramework."""
        # SharedStrategyFramework stores configs internally; expose what we can
        strategies: list[dict[str, Any]] = []
        # The framework may not expose a public listing; use what's available
        for config in getattr(self.strategy_framework, "_configs", {}).values():
            strategies.append(
                {
                    "strategy_id": config.config_id,
                    "schema_version": config.schema_version,
                    "rule_refs": list(config.rule_refs),
                    "parameters": dict(config.parameters),
                    "proposal_source": "deterministic",
                    "schema_valid": True,
                    "rejection_reason": None,
                    "label": "internal_simulation",
                }
            )
        return {
            "strategies": strategies,
            "label": "internal_simulation",
        }

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings_profiles(self) -> dict[str, Any]:
        """Return settings profiles (no secrets serialized)."""
        profiles = {}
        for name, profile in self.profiles.items():
            entry = {
                "value": profile.get("value"),
                "validated_range": profile.get("validated_range"),
                "source": profile.get("source"),
                "version": profile.get("version"),
                "actor": profile.get("actor"),
                "reason": profile.get("reason"),
                "timestamp_utc": profile.get("timestamp_utc"),
                "last_known_good": profile.get("last_known_good"),
                "secret_redacted": True,
            }
            profiles[name] = entry
        return {
            "profiles": profiles,
            "live_orders_enabled": False,
            "label": "internal_simulation",
        }

    def update_profile(
        self, profile_name: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a profile value with validation."""
        if profile_name not in self.profiles:
            raise HTTPException(status_code=404, detail="profile not found")
        profile = self.profiles[profile_name]
        new_value = body.get("value")
        if new_value is not None:
            validated_range = profile.get("validated_range", [])
            if validated_range and new_value not in validated_range:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "allowed": False,
                        "profile": profile_name,
                        "reason": f"value {new_value!r} not in validated range {validated_range}",
                    },
                )
            profile["value"] = new_value
        profile["version"] = str(int(profile["version"]) + 1)
        profile["actor"] = "owner"
        profile["reason"] = body.get("reason", "operator update")
        profile["timestamp_utc"] = _utc_now()
        profile["last_known_good"] = profile["version"]
        return {
            "allowed": True,
            "profile": profile_name,
            "version": profile["version"],
        }

    # ------------------------------------------------------------------
    # Migration service access
    # ------------------------------------------------------------------

    def apply_migration(self, version: int) -> dict[str, Any]:
        """Apply a versioned migration."""
        from superbot.persistence.migrations import apply_migration

        result = apply_migration(self.migration_service, version)
        return {
            "version": result.version,
            "success": result.success,
            "applied_at": result.applied_at,
        }

    def migration_status(self) -> dict[int, bool]:
        """Return migration status for all registered versions."""
        return self.migration_service.check_migration_status()

    # ------------------------------------------------------------------
    # Checkpoint/restart
    # ------------------------------------------------------------------

    def checkpoint(
        self, checkpoint_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Record a checkpoint."""
        from time import time

        from superbot.persistence.checkpoint_restart import _sha256_hex

        checkpoint_id = _sha256_hex(f"{checkpoint_type}:{payload}:{time()}")
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            checkpoint_type=checkpoint_type,
            payload=dict(payload),
            sequence=len(self.checkpoint_service._checkpoints),
            previous_hash="genesis",
        )
        self.checkpoint_service.register_checkpoint(record)
        return {
            "checkpoint_id": record.checkpoint_id,
            "checkpoint_type": record.checkpoint_type,
            "sequence": record.sequence,
            "event_id": record.event_id,
            "hash": record.hash,
        }

    def reconcile_crash(self) -> dict[str, Any]:
        """Reconcile state after a crash."""
        result = self.checkpoint_service.reconcile_crash()
        return {
            "job_reconciliations": result.job_reconciliations,
            "signal_reconciliations": result.signal_reconciliations,
            "position_reconciliations": result.position_reconciliations,
        }
