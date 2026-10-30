"""RED tests for M11.2 — FastAPI backend-driven state for all dashboard surfaces.

Covers: overview/health, data explorer labels, research queue jobs,
strategy/signal workbench, validation/experiment gate states,
portfolio/risk/internal simulation, audit/experiment library, settings/profiles.

Acceptance: backend-driven state (not mocked success), explicit synthetic/source
labels, no fake success or live-order controls, no public exposure, backend
enforces authorization (hiding a button is insufficient), gate states distinguish
PASS/FAIL/BLOCKED/NOT RUN, rejected signal/job includes reason and evidence.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from superbot.m11.api import create_app


def _client() -> TestClient:
    return TestClient(create_app())


# --- Overview / health ------------------------------------------------------

def test_health_returns_all_components():
    """Health row reports API, PostgreSQL, worker supervisor, model runtime,
    MT5 read-only status, last update, data freshness and backup state."""
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    components = data["components"]
    for name in (
        "api",
        "postgresql",
        "worker_supervisor",
        "model_runtime",
        "mt5_readonly",
    ):
        assert name in components
        assert components[name]["status"] in ("healthy", "degraded", "blocked")
    assert "last_update_utc" in data
    assert "data_freshness" in data
    assert "backup_state" in data


def test_health_overall_reflects_worst_component():
    """Overall status is blocked when any component is blocked."""
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    statuses = [c["status"] for c in data["components"].values()]
    if "blocked" in statuses:
        assert data["overall"] == "blocked"
    elif "degraded" in statuses:
        assert data["overall"] == "degraded"
    else:
        assert data["overall"] == "healthy"


# --- Data explorer / source labels ------------------------------------------

def test_data_explorer_labels_source_and_not_live():
    """OHLCV chart metadata distinguishes synthetic fixture / imported history /
    broker feed and never implies live broker data."""
    client = _client()
    response = client.get("/data/explorer/XAUUSD/M5")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] in ("synthetic_fixture", "imported_history", "broker_feed")
    assert data["live"] is False
    assert "label" in data
    assert "timeframe" in data
    assert "freshness" in data
    assert "coverage" in data


# --- Research queue jobs -----------------------------------------------------

def test_jobs_returns_status_and_lifecycle_fields():
    """Job status, dataset/symbol/timeframe, strategy/config version, priority,
    resource use, progress/checkpoint, start/duration, pause/resume/cancel."""
    client = _client()
    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["jobs"], list)
    for job in data["jobs"]:
        for field in (
            "job_id",
            "status",
            "dataset",
            "symbol",
            "timeframe",
            "strategy_version",
            "config_version",
            "priority",
            "resource_use",
            "progress",
            "checkpoint",
            "started_at_utc",
            "duration_seconds",
            "pause_available",
            "resume_available",
            "cancel_available",
        ):
            assert field in job, f"missing {field}"


def test_jobs_prevents_duplicate_overlaps():
    """Prevent duplicate overlaps; show why blocked/deferred."""
    client = _client()
    response = client.get("/jobs?check_duplicates=1")
    assert response.status_code == 200
    data = response.json()
    assert "duplicate_checks" in data


def test_job_cancel_requires_confirmation_when_uncheckpointed():
    """Confirm potentially destructive cancellation when uncheckpointed work
    could be lost."""
    client = _client()
    response = client.post("/jobs/job-1/cancel", json={"confirm_destructive": False})
    assert response.status_code == 400
    data = response.json()
    assert data["blocked"] is True
    assert "reason" in data


# --- Strategy/signal workbench -----------------------------------------------

def test_strategies_return_lifecycle_and_rejection_reason():
    """Strategy family/version/parameters, rules, proposal source, evidence refs,
    schema validation outcome, signal ID, rejection reason."""
    client = _client()
    response = client.get("/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["strategies"], list)
    for strategy in data["strategies"]:
        for field in (
            "strategy_id",
            "family",
            "version",
            "parameters",
            "lifecycle",
            "proposal_source",
            "schema_valid",
            "rejection_reason",
            "signal_id",
        ):
            assert field in strategy, f"missing {field}"
        assert strategy["lifecycle"] in (
            "proposed",
            "blocked",
            "validating",
            "shadow",
            "internal_simulation",
            "archived",
        )


def test_ai_suggestion_never_presented_as_approved():
    """Rejected signal shows deterministic rejection reason. Never present an AI
    suggestion as approved trade."""
    client = _client()
    response = client.get("/strategies/strategy-ai-1")
    assert response.status_code == 200
    data = response.json()
    if data["proposal_source"] == "ai":
        assert data["lifecycle"] != "approved"
        assert data["rejection_reason"] is not None


# --- Validation / experiment gate states -------------------------------------

def test_experiments_gate_states_distinguished():
    """Each gate explicitly shows PASS, FAIL, BLOCKED or NOT RUN, with
    timestamp/config/evidence."""
    client = _client()
    response = client.get("/experiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["experiments"], list)
    for experiment in data["experiments"]:
        for gate in experiment.get("gates", []):
            assert gate["state"] in ("PASS", "FAIL", "BLOCKED", "NOT RUN")
            assert "timestamp_utc" in gate
            assert "config_ref" in gate
            assert "evidence_ref" in gate


def test_failed_experiments_remain_searchable():
    """Failed experiments remain searchable; no silent deletion."""
    client = _client()
    response = client.get("/experiments?outcome=failed")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["experiments"], list)


# --- Portfolio / risk / internal simulation ----------------------------------

def test_risk_returns_positions_and_limits():
    """Simulated positions, entry/exit, stop/partial event timeline,
    mark-to-market inputs, costs, exposure and P&L."""
    client = _client()
    response = client.get("/risk")
    assert response.status_code == 200
    data = response.json()
    assert "positions" in data
    assert "exposure" in data
    assert "pnl" in data
    assert "daily_loss_usage_pct" in data
    assert "drawdown_peak_pct" in data
    assert "halt_state" in data
    assert data["label"] == "internal_simulation"


def test_missing_stale_specs_show_blocked_not_zero_risk():
    """Missing/stale specs or unverifiable sizing must show blocked, never
    zero-risk/green."""
    client = _client()
    response = client.get("/risk/strategy/missing-spec-strategy")
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is True
    assert data["risk_state"] != "green"
    assert "reason" in data


# --- Audit / experiment library ----------------------------------------------

def test_audit_returns_append_only_events_with_refs():
    """Search run ID, strategy/version, symbol/timeframe, date, data hash,
    outcome, gate, failure class and commit. Inspect append-only events,
    evidence refs, correction linkage and version refs."""
    client = _client()
    response = client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["events"], list)
    for event in data["events"]:
        for field in (
            "event_id",
            "run_id",
            "strategy_version",
            "symbol",
            "timeframe",
            "date_utc",
            "data_hash",
            "outcome",
            "gate",
            "failure_class",
            "commit",
        ):
            assert field in event, f"missing {field}"


def test_audit_chain_integrity():
    """Append-only events remain verifiable; corrections never modify originals."""
    client = _client()
    response = client.get("/audit/chain/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["chain_intact"] is True


# --- Settings / profiles -----------------------------------------------------

def test_settings_returns_profiles_with_metadata():
    """research, internal-simulation, future guarded demo-readiness with clear
    stage boundaries. Show value, validated range/source, version, actor/reason,
    timestamp and last-known-good."""
    client = _client()
    response = client.get("/settings/profiles")
    assert response.status_code == 200
    data = response.json()
    profiles = data["profiles"]
    assert "research" in profiles
    assert "internal_simulation" in profiles
    for profile in profiles.values():
        for field in (
            "value",
            "validated_range",
            "source",
            "version",
            "actor",
            "reason",
            "timestamp_utc",
            "last_known_good",
        ):
            assert field in profile, f"missing {field}"


def test_settings_secrets_redacted_and_nonexportable():
    """Secrets redacted and non-exportable."""
    client = _client()
    response = client.get("/settings/profiles?include_secrets=1")
    assert response.status_code == 200
    data = response.json()
    for profile in data["profiles"].values():
        assert profile.get("secret_redacted") is True or "secret" not in profile


def test_settings_no_live_order_control():
    """No control to enable live orders in this scope."""
    client = _client()
    response = client.get("/settings/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["live_orders_enabled"] is False


def test_settings_only_authorized_owner_can_change():
    """Only authorized owner may change sensitive settings."""
    client = _client()
    response = client.post(
        "/settings/profiles/research",
        json={"value": "tampered"},
        headers={"X-Operator-Role": "viewer"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["allowed"] is False


# --- No public exposure ------------------------------------------------------

def test_api_bind_localhost_only():
    """No public network binding; remote access only through approved private VPN."""
    client = _client()
    # The app should not advertise a public host; check openapi/server URL is local
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    servers = openapi.json().get("servers", [])
    for server in servers:
        url = server.get("url", "")
        assert "0.0.0.0" not in url
        assert "public" not in url.lower()
