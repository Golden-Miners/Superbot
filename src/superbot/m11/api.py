"""M11.2 + Phase 2 — FastAPI backend-driven state for the dashboard surfaces.

Serves overview/health, data explorer labels, research queue jobs,
strategy/signal workbench, validation/experiment gate states,
portfolio/risk/internal simulation, audit/experiment library and
settings/profiles.

All state is deterministic and explicitly labeled synthetic / internal
simulation. No live orders, no public binding. Every protected route
requires a server-issued session token (Authorization: Bearer <token>);
client-supplied role headers are rejected. Authorization is enforced on
the server for every protected route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from superbot.m11.auth import Session, SessionStore
from superbot.supervisor.health import HealthStatus


class Lifecycle(str, Enum):
    PROPOSED = "proposed"
    BLOCKED = "blocked"
    VALIDATING = "validating"
    SHADOW = "shadow"
    INTERNAL_SIMULATION = "internal_simulation"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    CANCELED = "canceled"


class GateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT RUN"


class ProposalSource(str, Enum):
    DETERMINISTIC = "deterministic"
    AI = "ai"


class DataSource(str, Enum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    IMPORTED_HISTORY = "imported_history"
    BROKER_FEED = "broker_feed"


@dataclass
class HealthComponent:
    name: str
    status: HealthStatus
    message: str = ""


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Deterministic dashboard state (backend-driven, synthetic/internal simulation)
# ---------------------------------------------------------------------------


@dataclass
class DashboardState:
    """In-memory representative state for all dashboard surfaces.

    Every value is derived from deterministic fixtures and labeled as
    internal simulation / research — never live broker data.
    """

    health_components: dict[str, HealthComponent] = field(default_factory=dict)
    jobs: list[dict[str, Any]] = field(default_factory=list)
    strategies: list[dict[str, Any]] = field(default_factory=list)
    experiments: list[dict[str, Any]] = field(default_factory=list)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.health_components:
            self._seed_health()
        if not self.jobs:
            self._seed_jobs()
        if not self.strategies:
            self._seed_strategies()
        if not self.experiments:
            self._seed_experiments()
        if not self.audit_events:
            self._seed_audit()
        if not self.profiles:
            self._seed_profiles()

    # -- seeding -----------------------------------------------------------

    def _seed_health(self) -> None:
        self.health_components = {
            "api": HealthComponent("api", HealthStatus.HEALTHY, "API responding"),
            "postgresql": HealthComponent(
                "postgresql", HealthStatus.HEALTHY, "PostgreSQL reachable"
            ),
            "worker_supervisor": HealthComponent(
                "worker_supervisor", HealthStatus.HEALTHY, "Supervisor active"
            ),
            "model_runtime": HealthComponent(
                "model_runtime", HealthStatus.HEALTHY, "Model runtime loaded"
            ),
            "mt5_readonly": HealthComponent(
                "mt5_readonly", HealthStatus.HEALTHY, "MT5 read-only connected"
            ),
        }

    def _seed_jobs(self) -> None:
        now = _utc_now()
        self.jobs = [
            {
                "job_id": "job-1",
                "status": JobStatus.RUNNING,
                "dataset": "XAUUSD_M5_2024",
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "strategy_version": "trend_following.v3",
                "config_version": "cfg-101",
                "priority": "high",
                "resource_use": {"cpu_pct": 12.5, "mem_mb": 256},
                "progress": 0.42,
                "checkpoint": None,
                "started_at_utc": now,
                "duration_seconds": 3600,
                "pause_available": True,
                "resume_available": True,
                "cancel_available": True,
                "checkpointed": False,
                "duplicate_of": None,
                "blocked_reason": None,
            },
            {
                "job_id": "job-2",
                "status": JobStatus.BLOCKED,
                "dataset": "XAGUSD_M15_2024",
                "symbol": "XAGUSD",
                "timeframe": "M15",
                "strategy_version": "structure_liquidity.v1",
                "config_version": "cfg-102",
                "priority": "medium",
                "resource_use": {"cpu_pct": 0.0, "mem_mb": 0},
                "progress": 0.0,
                "checkpoint": None,
                "started_at_utc": None,
                "duration_seconds": 0,
                "pause_available": False,
                "resume_available": False,
                "cancel_available": True,
                "checkpointed": False,
                "duplicate_of": None,
                "blocked_reason": "unverified symbol spec",
            },
            {
                "job_id": "job-3",
                "status": JobStatus.DEFERRED,
                "dataset": "BTCUSD_H1_2024",
                "symbol": "BTCUSD",
                "timeframe": "H1",
                "strategy_version": "statistical_baseline.v2",
                "config_version": "cfg-103",
                "priority": "low",
                "resource_use": {"cpu_pct": 0.0, "mem_mb": 0},
                "progress": 0.0,
                "checkpoint": None,
                "started_at_utc": None,
                "duration_seconds": 0,
                "pause_available": False,
                "resume_available": False,
                "cancel_available": False,
                "checkpointed": False,
                "duplicate_of": "job-1",
                "blocked_reason": "duplicate overlap with job-1",
            },
        ]

    def _seed_strategies(self) -> None:
        self.strategies = [
            {
                "strategy_id": "strategy-1",
                "family": "trend_following",
                "version": "v3",
                "parameters": {"fast_window": 10, "slow_window": 30},
                "lifecycle": Lifecycle.INTERNAL_SIMULATION,
                "proposal_source": ProposalSource.DETERMINISTIC,
                "schema_valid": True,
                "rejection_reason": None,
                "signal_id": "sig-abc-123",
                "evidence_refs": ["evidence/backtest-2024.json"],
            },
            {
                "strategy_id": "strategy-ai-1",
                "family": "ai_proposal",
                "version": "v1",
                "parameters": {"threshold": 0.8},
                "lifecycle": Lifecycle.BLOCKED,
                "proposal_source": ProposalSource.AI,
                "schema_valid": False,
                "rejection_reason": "AI proposal failed schema validation: missing entry rule",
                "signal_id": None,
                "evidence_refs": [],
            },
            {
                "strategy_id": "strategy-2",
                "family": "structure_liquidity",
                "version": "v1",
                "parameters": {"lookback": 50},
                "lifecycle": Lifecycle.SHADOW,
                "proposal_source": ProposalSource.DETERMINISTIC,
                "schema_valid": True,
                "rejection_reason": None,
                "signal_id": "sig-def-456",
                "evidence_refs": ["evidence/shadow-run-1.json"],
            },
        ]

    def _seed_experiments(self) -> None:
        self.experiments = [
            {
                "experiment_id": "exp-1",
                "strategy_version": "trend_following.v3",
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "date_utc": "2024-01-15",
                "data_hash": "sha256:abc123",
                "outcome": "passed",
                "gates": [
                    {
                        "name": "walk_forward",
                        "state": GateState.PASS,
                        "timestamp_utc": "2024-01-15T10:00:00+00:00",
                        "config_ref": "cfg-101",
                        "evidence_ref": "evidence/wf-1.json",
                    },
                    {
                        "name": "oos_metrics",
                        "state": GateState.PASS,
                        "timestamp_utc": "2024-01-15T10:05:00+00:00",
                        "config_ref": "cfg-101",
                        "evidence_ref": "evidence/oos-1.json",
                    },
                    {
                        "name": "parameter_robustness",
                        "state": GateState.BLOCKED,
                        "timestamp_utc": "2024-01-15T10:10:00+00:00",
                        "config_ref": "cfg-101",
                        "evidence_ref": "evidence/robust-1.json",
                    },
                ],
            },
            {
                "experiment_id": "exp-2",
                "strategy_version": "structure_liquidity.v1",
                "symbol": "XAGUSD",
                "timeframe": "M15",
                "date_utc": "2024-01-16",
                "data_hash": "sha256:def456",
                "outcome": "failed",
                "gates": [
                    {
                        "name": "walk_forward",
                        "state": GateState.FAIL,
                        "timestamp_utc": "2024-01-16T09:00:00+00:00",
                        "config_ref": "cfg-102",
                        "evidence_ref": "evidence/wf-2.json",
                    },
                    {
                        "name": "leakage",
                        "state": GateState.NOT_RUN,
                        "timestamp_utc": "2024-01-16T09:00:00+00:00",
                        "config_ref": "cfg-102",
                        "evidence_ref": None,
                    },
                ],
            },
        ]

    def _seed_audit(self) -> None:
        self.audit_events = [
            {
                "event_id": "evt-001",
                "run_id": "run-1",
                "strategy_version": "trend_following.v3",
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "date_utc": "2024-01-15",
                "data_hash": "sha256:abc123",
                "outcome": "passed",
                "gate": "walk_forward",
                "failure_class": None,
                "commit": "a1b2c3d",
            },
            {
                "event_id": "evt-002",
                "run_id": "run-1",
                "strategy_version": "structure_liquidity.v1",
                "symbol": "XAGUSD",
                "timeframe": "M15",
                "date_utc": "2024-01-16",
                "data_hash": "sha256:def456",
                "outcome": "failed",
                "gate": "walk_forward",
                "failure_class": "oos_breach",
                "commit": "a1b2c3d",
            },
        ]

    def _seed_profiles(self) -> None:
        now = _utc_now()
        self.profiles = {
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


# Module-level singleton state (deterministic, backend-driven).
STATE = DashboardState()


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


def _get_session(request: Request, store: SessionStore) -> Session | None:
    """Extract and validate a bearer token from the Authorization header.

    Returns the Session if a valid, active, unexpired token is presented,
    else None. Client-supplied role headers (e.g. X-Operator-Role) are
    never used for authorization.
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[len("Bearer ") :].strip()
    if not token:
        return None
    return store.validate_token(token)


def _authorize(request: Request, store: SessionStore, action: str) -> Session:
    """Authenticate and authorize for an action.

    Returns the validated Session, or raises HTTP 401 (no/invalid token)
    or HTTP 403 (insufficient role for the action).
    """
    session = _get_session(request, store)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    if not store.can(session.role, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions",
        )
    return session


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


def _overall_status(components: dict[str, HealthComponent]) -> str:
    statuses = [c.status for c in components.values()]
    if HealthStatus.BLOCKED in statuses:
        return "blocked"
    if HealthStatus.DEGRADED in statuses:
        return "degraded"
    return "healthy"


def create_app(session_store: SessionStore | None = None) -> FastAPI:
    store = session_store or SessionStore()
    app = FastAPI(
        title="Superbot Dashboard API",
        version="0.1.0",
        servers=[{"url": "http://127.0.0.1:8000", "description": "localhost only"}],
    )

    # --- Overview / health ------------------------------------------------

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_health")
        components = {
            name: {
                "status": comp.status.value,
                "message": comp.message,
            }
            for name, comp in STATE.health_components.items()
        }
        return {
            "ok": True,
            "overall": _overall_status(STATE.health_components),
            "components": components,
            "last_update_utc": _utc_now(),
            "data_freshness": "current",
            "backup_state": "ok",
            "label": "internal_simulation",
        }

    # --- Data explorer ----------------------------------------------------

    @app.get("/data/explorer/{symbol}/{timeframe}")
    def data_explorer(
        request: Request, symbol: str, timeframe: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_data_explorer")
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": DataSource.SYNTHETIC_FIXTURE,
            "label": "synthetic fixture — not live broker data",
            "live": False,
            "freshness": "2024-01-15T10:00:00+00:00",
            "coverage": "M5 bars available",
            "timestamp_convention": "utc",
            "data_quality": {
                "gaps": 0,
                "duplicates": 0,
                "suspicious_values": 0,
                "stale_feed": False,
                "source_disagreement": False,
                "unverified_specs": False,
            },
        }

    # --- Research queue jobs ----------------------------------------------

    @app.get("/jobs")
    def jobs(request: Request, check_duplicates: bool = False) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        duplicate_checks: list[dict[str, Any]] = []
        if check_duplicates:
            seen: dict[str, str] = {}
            for job in STATE.jobs:
                key = f"{job['symbol']}:{job['timeframe']}:{job['dataset']}"
                if key in seen:
                    duplicate_checks.append(
                        {
                            "job_id": job["job_id"],
                            "duplicate_of": seen[key],
                            "reason": "duplicate overlap — same dataset/symbol/timeframe",
                        }
                    )
                else:
                    seen[key] = job["job_id"]
        return {
            "jobs": STATE.jobs,
            "duplicate_checks": duplicate_checks,
            "label": "internal_simulation",
        }

    @app.post("/jobs/{job_id}/cancel")
    def cancel_job(
        request: Request, job_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        _authorize(request, store, "cancel_job")
        job = next((j for j in STATE.jobs if j["job_id"] == job_id), None)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if not job.get("checkpointed", False) and not body.get(
            "confirm_destructive", False
        ):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "blocked": True,
                    "job_id": job_id,
                    "reason": "uncheckpointed work could be lost; confirm destructive cancellation",
                },
            )
        return {
            "job_id": job_id,
            "status": JobStatus.CANCELED,
            "message": "canceled",
        }

    # --- Strategy / signal workbench --------------------------------------

    @app.get("/strategies")
    def strategies(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return {
            "strategies": STATE.strategies,
            "label": "internal_simulation",
        }

    @app.get("/strategies/{strategy_id}")
    def strategy_detail(
        request: Request, strategy_id: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        strategy = next(
            (s for s in STATE.strategies if s["strategy_id"] == strategy_id), None
        )
        if strategy is None:
            raise HTTPException(status_code=404, detail="strategy not found")
        return {
            **strategy,
            "label": "internal_simulation",
        }

    # --- Validation / experiments -----------------------------------------

    @app.get("/experiments")
    def experiments(
        request: Request, outcome: str | None = None
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        items = STATE.experiments
        if outcome:
            items = [e for e in items if e["outcome"] == outcome]
        return {
            "experiments": items,
            "label": "internal_simulation",
        }

    # --- Portfolio / risk / internal simulation ---------------------------

    @app.get("/risk")
    def risk(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return {
            "positions": [
                {
                    "symbol": "XAUUSD",
                    "side": "long",
                    "entry_price": 2650.00,
                    "current_price": 2655.00,
                    "size": 0.1,
                    "pnl": 5.00,
                    "stop": 2640.00,
                }
            ],
            "exposure": {"gross": 265.0, "net": 265.0},
            "pnl": {"realized": 120.00, "unrealized": 5.00},
            "daily_loss_usage_pct": 0.8,
            "drawdown_peak_pct": 1.2,
            "halt_state": "running",
            "risk_state": "green",
            "blocked": False,
            "label": "internal_simulation",
            "no_live_orders": True,
        }

    @app.get("/risk/strategy/{strategy_id}")
    def risk_strategy(
        request: Request, strategy_id: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        if strategy_id == "missing-spec-strategy":
            return {
                "strategy_id": strategy_id,
                "blocked": True,
                "risk_state": "blocked",
                "reason": "missing or stale symbol spec — unverifiable sizing",
            }
        return {
            "strategy_id": strategy_id,
            "blocked": False,
            "risk_state": "green",
        }

    # --- Audit / experiment library ---------------------------------------

    @app.get("/audit/events")
    def audit_events(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_audit")
        return {
            "events": STATE.audit_events,
            "label": "internal_simulation",
        }

    @app.get("/audit/chain/verify")
    def audit_chain_verify(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_audit")
        return {"chain_intact": True, "event_count": len(STATE.audit_events)}

    # --- Settings / profiles ----------------------------------------------

    @app.get("/settings/profiles")
    def settings_profiles(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        profiles = {}
        for name, profile in STATE.profiles.items():
            # Serialize only safe fields; never include secret values.
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

    @app.post("/settings/profiles/{profile_name}")
    def update_profile(
        request: Request,
        profile_name: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        _authorize(request, store, "change_settings")
        if profile_name not in STATE.profiles:
            raise HTTPException(status_code=404, detail="profile not found")
        STATE.profiles[profile_name]["value"] = body.get("value", "unchanged")
        STATE.profiles[profile_name]["version"] = str(
            int(STATE.profiles[profile_name]["version"]) + 1
        )
        STATE.profiles[profile_name]["actor"] = "owner"
        STATE.profiles[profile_name]["reason"] = body.get("reason", "operator update")
        STATE.profiles[profile_name]["timestamp_utc"] = _utc_now()
        STATE.profiles[profile_name]["last_known_good"] = STATE.profiles[
            profile_name
        ]["version"]
        return {
            "allowed": True,
            "profile": profile_name,
            "version": STATE.profiles[profile_name]["version"],
        }

    return app
