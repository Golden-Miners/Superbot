"""RED tests for Phase 2 Security — Session-based API authentication.

Covers: unauthenticated access (401), invalid token (401), viewer/owner
permissions, session expiry, session revocation, no `include_secrets`
parameter, and no secret values serialized in any API response.

Acceptance: backend enforces authorization via server-issued sessions;
client-supplied role headers are rejected; secrets never serialized in API
responses; every protected route requires a valid session token.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from superbot.m11.api import create_app
from superbot.m11.auth import Role, SessionStore


def _make_client(token: str | None = None) -> tuple[TestClient, SessionStore]:
    """Create a TestClient backed by a shared SessionStore.

    If token is None, no Authorization header is sent (unauthenticated).
    """
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    if token is not None:
        client.headers["Authorization"] = f"Bearer {token}"
    return client, store


def _owner_token(store: SessionStore) -> str:
    _, token = store.create_session(Role.OWNER)
    return token


def _viewer_token(store: SessionStore) -> str:
    _, token = store.create_session(Role.VIEWER)
    return token


def _operator_token(store: SessionStore) -> str:
    _, token = store.create_session(Role.OPERATOR)
    return token


# --- Unauthenticated access ------------------------------------------------

def test_unauthenticated_health_returns_401():
    """No Authorization header on a protected route returns 401."""
    client, _ = _make_client()
    response = client.get("/health")
    assert response.status_code == 401


def test_unauthenticated_data_explorer_returns_401():
    """Data explorer requires authentication."""
    client, _ = _make_client()
    response = client.get("/data/explorer/XAUUSD/M5")
    assert response.status_code == 401


def test_unauthenticated_jobs_returns_401():
    """Jobs endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/jobs")
    assert response.status_code == 401


def test_unauthenticated_strategies_returns_401():
    """Strategies endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/strategies")
    assert response.status_code == 401


def test_unauthenticated_experiments_returns_401():
    """Experiments endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/experiments")
    assert response.status_code == 401


def test_unauthenticated_risk_returns_401():
    """Risk endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/risk")
    assert response.status_code == 401


def test_unauthenticated_audit_returns_401():
    """Audit endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/audit/events")
    assert response.status_code == 401


def test_unauthenticated_settings_returns_401():
    """Settings endpoint requires authentication."""
    client, _ = _make_client()
    response = client.get("/settings/profiles")
    assert response.status_code == 401


def test_invalid_token_returns_401():
    """An invalid bearer token returns 401."""
    client = TestClient(create_app())
    client.headers["Authorization"] = "Bearer invalid-token"
    response = client.get("/health")
    assert response.status_code == 401


def test_empty_token_returns_401():
    """An empty bearer token returns 401."""
    client = TestClient(create_app())
    client.headers["Authorization"] = "Bearer "
    response = client.get("/health")
    assert response.status_code == 401


# --- Viewer permissions ----------------------------------------------------

def test_viewer_can_read_health():
    """A viewer with a valid token can read health."""
    client, _ = _make_client(_viewer_token(SessionStore()))
    # _make_client creates its own store; we need a shared store.
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_viewer_token(store)}"
    response = client.get("/health")
    assert response.status_code == 200


def test_viewer_can_read_data_explorer():
    """A viewer can read the data explorer."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_viewer_token(store)}"
    response = client.get("/data/explorer/XAUUSD/M5")
    assert response.status_code == 200
    assert response.json()["live"] is False


def test_viewer_can_read_strategies():
    """A viewer can read strategies."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_viewer_token(store)}"
    response = client.get("/strategies")
    assert response.status_code == 200


def test_viewer_can_read_risk():
    """A viewer can read risk state."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_viewer_token(store)}"
    response = client.get("/risk")
    assert response.status_code == 200


# --- Viewer cannot change settings -----------------------------------------

def test_viewer_cannot_change_settings():
    """A viewer with a valid token cannot change settings (403)."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_viewer_token(store)}"
    response = client.post("/settings/profiles/research", json={"value": "tampered"})
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "insufficient permissions"


def test_operator_cannot_change_settings():
    """An operator with a valid token cannot change settings (403)."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_operator_token(store)}"
    response = client.post("/settings/profiles/research", json={"value": "tampered"})
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "insufficient permissions"


# --- Owner permissions -----------------------------------------------------

def test_owner_can_change_settings():
    """An owner with a valid token can change settings (200)."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_owner_token(store)}"
    response = client.post("/settings/profiles/research", json={"value": "tampered"})
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert data["profile"] == "research"


# --- Session expiry --------------------------------------------------------

def test_expired_session_returns_401():
    """An expired session returns 401 on every protected route."""
    store = SessionStore()
    _, token = store.create_session(Role.OWNER)
    store._sessions[token].expires_at_utc = "1970-01-01T00:00:00+00:00"
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {token}"
    response = client.get("/health")
    assert response.status_code == 401


# --- Session revocation ----------------------------------------------------

def test_revoked_session_returns_401():
    """A revoked session returns 401 on every protected route."""
    store = SessionStore()
    _session, token = store.create_session(Role.OWNER)
    assert store.invalidate_token(token) is True
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {token}"
    response = client.get("/health")
    assert response.status_code == 401


# --- No include_secrets parameter -----------------------------------------

def test_settings_rejects_include_secrets():
    """The include_secrets query parameter is removed and does not expose
    secrets."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_owner_token(store)}"
    response = client.get("/settings/profiles?include_secrets=1")
    # Parameter is ignored/removed; response must not expose secrets.
    assert response.status_code == 200
    data = response.json()
    for profile in data["profiles"].values():
        assert "secret" not in profile


# --- No secret values serialized ------------------------------------------

def test_settings_response_contains_no_secret_values():
    """No profile value in the response exposes a plaintext secret."""
    store = SessionStore()
    client = TestClient(create_app(session_store=store))
    client.headers["Authorization"] = f"Bearer {_owner_token(store)}"
    response = client.get("/settings/profiles")
    assert response.status_code == 200
    data = response.json()
    for profile in data["profiles"].values():
        # secret_redacted is expected; no plaintext secret value should appear.
        assert profile.get("secret_redacted") is True
        for key, val in profile.items():
            if key == "secret_redacted":
                continue
            assert val is not None
            assert "secret" not in str(val).lower()


def test_dummy_secret_not_exposed_in_api_response():
    """A profile with a dummy secret value never exposes it via the API."""
    store = SessionStore()
    # Inject a profile with a dummy secret directly into state.
    # This tests that the API serialization path redacts it.
    from superbot.m11.api import STATE

    STATE.profiles["dummy_secret_profile"] = {
        "value": "enabled",
        "validated_range": ["enabled", "disabled"],
        "source": "config.yaml",
        "version": "1",
        "actor": "owner",
        "reason": "test",
        "timestamp_utc": "2024-01-01T00:00:00+00:00",
        "last_known_good": "1",
        "secret_redacted": True,
        "secret": "dummy_secret_value_do_not_expose",
    }
    try:
        client = TestClient(create_app(session_store=store))
        client.headers["Authorization"] = f"Bearer {_owner_token(store)}"
        response = client.get("/settings/profiles")
        assert response.status_code == 200
        body = str(response.json())
        assert "dummy_secret_value_do_not_expose" not in body
        # secret_redacted is expected; no plaintext secret value should appear.
        for profile in response.json()["profiles"].values():
            assert profile.get("secret_redacted") is True
            for key, val in profile.items():
                if key == "secret_redacted":
                    continue
                assert "dummy_secret_value_do_not_expose" not in str(val)
    finally:
        del STATE.profiles["dummy_secret_profile"]
