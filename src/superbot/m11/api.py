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
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from superbot.m11.auth import Session, SessionStore
from superbot.m11.integration import DashboardService
from superbot.m11.mt5_data_provider import MT5DataProvider
from superbot.persistence.audit_linkage import verify_audit_chain
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
    CANCEL_REQUESTED = "cancel_requested"
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
        # Start empty — no synthetic fixture data is seeded into production state.
        # All surfaces must source data from real services (health registry, job
        # scheduler, strategy framework, experiment registry, MT5 provider) or
        # report NOT_AVAILABLE when no data is available.
        pass


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


def create_app(
    session_store: SessionStore | None = None,
    dashboard_service: DashboardService | None = None,
    mt5_data_provider: MT5DataProvider | None = None,
) -> FastAPI:
    store = session_store or SessionStore()
    dashboard = dashboard_service or DashboardService()
    mt5 = mt5_data_provider or MT5DataProvider()
    app = FastAPI(
        title="Superbot Dashboard API",
        version="0.1.0",
        servers=[{"url": "http://127.0.0.1:8000", "description": "localhost only"}],
    )
    app.state.mt5_provider = mt5

    # --- Overview / health ------------------------------------------------

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_health")
        health_data = dashboard.get_health()
        # Report MT5 connectivity status from the live provider
        if mt5.is_connected():
            health_data["components"]["mt5_readonly"] = {
                "status": "healthy",
                "message": "MT5 terminal connected — read-only",
            }
        else:
            health_data["components"]["mt5_readonly"] = {
                "status": "blocked",
                "message": "MT5 terminal not connected",
            }
        return health_data

    # --- Data explorer ----------------------------------------------------

    @app.get("/data/explorer/{symbol}/{timeframe}")
    def data_explorer(
        request: Request, symbol: str, timeframe: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_data_explorer")
        # Return live broker data from MT5 provider
        mt5 = app.state.mt5_provider if hasattr(app.state, "mt5_provider") else None
        bars = mt5.get_ohlcv(symbol, timeframe, count=100) if mt5 else []
        tick = mt5.get_tick(symbol) if mt5 else None

        if bars:
            latest = bars[0]
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": DataSource.BROKER_FEED,
                "label": "broker feed — read-only, not live orders",
                "live": True,
                "freshness": latest.bar_open_utc.isoformat(),
                "coverage": f"{timeframe} bars available",
                "timestamp_convention": "utc",
                "data_quality": {
                    "gaps": 0,
                    "duplicates": 0,
                    "suspicious_values": 0,
                    "stale_feed": latest.quality_status == "stale",
                    "source_disagreement": False,
                    "unverified_specs": False,
                },
                "open": str(latest.open),
                "high": str(latest.high),
                "low": str(latest.low),
                "close": str(latest.close),
                "volume": str(latest.volume) if latest.volume else None,
            }
        elif tick:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": DataSource.BROKER_FEED,
                "label": "broker feed — read-only, not live orders",
                "live": tick.data_state.value == "live",
                "freshness": tick.timestamp_utc.isoformat(),
                "coverage": "tick data available",
                "timestamp_convention": "utc",
                "data_quality": {
                    "gaps": 0,
                    "duplicates": 0,
                    "suspicious_values": 0,
                    "stale_feed": tick.data_state.value == "stale",
                    "source_disagreement": False,
                    "unverified_specs": False,
                },
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
            }
        else:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": DataSource.BROKER_FEED,
                "label": "broker feed — read-only, not live orders",
                "live": False,
                "freshness": "unavailable",
                "coverage": "no data",
                "timestamp_convention": "utc",
                "data_quality": {
                    "gaps": 0,
                    "duplicates": 0,
                    "suspicious_values": 0,
                    "stale_feed": True,
                    "source_disagreement": False,
                    "unverified_specs": False,
                },
            }

    # --- Research queue jobs ----------------------------------------------

    @app.get("/jobs")
    def jobs(request: Request, check_duplicates: bool = False) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return dashboard.get_jobs()

    @app.post("/jobs/{job_id}/cancel")
    def cancel_job(
        request: Request, job_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        _authorize(request, store, "cancel_job")
        job = dashboard.job_scheduler.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        result = dashboard.job_scheduler.cancel_job(
            job_id, confirm_destructive=body.get("confirm_destructive", False)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="job not found")
        if not result.accepted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "blocked": True,
                    "job_id": job_id,
                    "reason": result.reason,
                },
            )
        return {
            "job_id": job_id,
            "status": JobStatus.CANCEL_REQUESTED,
            "message": result.reason,
        }

    # --- Strategy / signal workbench --------------------------------------

    @app.get("/strategies")
    def strategies(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return dashboard.get_strategies()

    @app.get("/strategies/{strategy_id}")
    def strategy_detail(
        request: Request, strategy_id: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        strategies = dashboard.get_strategies()
        strategy = next(
            (s for s in strategies["strategies"] if s["strategy_id"] == strategy_id),
            None,
        )
        if strategy is None:
            raise HTTPException(status_code=404, detail="strategy not found")
        return strategy

    # --- Validation / experiments -----------------------------------------

    @app.get("/experiments")
    def experiments(
        request: Request, outcome: str | None = None
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return dashboard.get_experiments()

    # --- Portfolio / risk / internal simulation ---------------------------

    @app.get("/risk")
    def risk(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return dashboard.get_risk()

    @app.get("/risk/strategy/{strategy_id}")
    def risk_strategy(
        request: Request, strategy_id: str
    ) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        risk_data = dashboard.get_risk()
        for s in risk_data.get("strategies", []):
            if s["strategy_id"] == strategy_id:
                current_dd_pct = Decimal(str(s["current_dd_pct"]))
                daily_loss_pct = Decimal(str(s["daily_loss_pct"]))
                max_dd_pct = Decimal(str(s["max_dd_pct"]))
                max_daily_loss_pct = Decimal(str(s["max_daily_loss_pct"]))
                blocked = current_dd_pct > max_dd_pct or daily_loss_pct > max_daily_loss_pct
                reasons = []
                if current_dd_pct > max_dd_pct:
                    reasons.append(f"drawdown {current_dd_pct}% exceeds limit {max_dd_pct}%")
                if daily_loss_pct > max_daily_loss_pct:
                    reasons.append(f"daily loss {daily_loss_pct}% exceeds limit {max_daily_loss_pct}%")
                return {
                    "strategy_id": strategy_id,
                    "blocked": blocked,
                    "risk_state": "blocked" if blocked else "green",
                    "reasons": reasons,
                    **s,
                }
        return {
            "strategy_id": strategy_id,
            "blocked": True,
            "risk_state": "blocked",
            "reason": "missing or stale symbol spec — unverifiable sizing",
        }

    # --- Audit / experiment library ---------------------------------------

    @app.get("/audit/events")
    def audit_events(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_audit")
        return dashboard.get_audit_events()

    @app.get("/audit/chain/verify")
    def audit_chain_verify(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_audit")
        events = dashboard.get_audit_events()
        chain_intact = verify_audit_chain(events["events"])
        return {
            "events": events["events"],
            "chain_intact": chain_intact,
            "audit_chain_valid": chain_intact,
            "label": "internal_simulation",
        }

    # --- Settings / profiles ----------------------------------------------

    @app.get("/settings/profiles")
    def settings_profiles(request: Request) -> dict[str, Any]:
        _authorize(request, store, "read_dashboard")
        return dashboard.get_settings_profiles()

    @app.post("/settings/profiles/{profile_name}")
    def update_profile(
        request: Request,
        profile_name: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        _authorize(request, store, "change_settings")
        return dashboard.update_profile(profile_name, body)

    return app
