"""RED tests for Phase 2 Security — Server-issued session authentication.

Covers: unpredictable server-issued session tokens, token-based validation,
session expiry and revocation, role-based authorization via session (not
client-supplied headers), and secret redaction.

Acceptance: backend enforces authorization via server-issued sessions;
client-supplied role headers are rejected; secrets never serialized in API
responses; unauthenticated access returns 401.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from superbot.m11.api import create_app
from superbot.m11.auth import (
    VPN_DOC_PATH,
    Role,
    Session,
    SessionStore,
    generate_session_token,
    is_localhost_host,
    redact_secret,
    validate_bind_host,
)


def test_generate_session_token_returns_nonempty_string():
    """generate_session_token returns a non-empty string token."""
    token = generate_session_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_session_tokens_are_unique():
    """Each call to create_session produces a unique token."""
    store = SessionStore()
    tokens = set()
    for _ in range(50):
        _, token = store.create_session(Role.VIEWER)
        tokens.add(token)
    assert len(tokens) == 50


def test_create_session_returns_session_and_token():
    """create_session returns a Session and an unpredictable token."""
    store = SessionStore()
    session, token = store.create_session(Role.OWNER)
    assert isinstance(session, Session)
    assert session.role == Role.OWNER
    assert session.is_active is True
    assert isinstance(token, str)
    assert len(token) > 0
    # Session ID must not equal the token (token is the secret, ID is metadata).
    assert session.session_id != token


def test_validate_token_returns_session():
    """A valid server-issued token validates to its session."""
    store = SessionStore()
    session, token = store.create_session(Role.OPERATOR)
    found = store.validate_token(token)
    assert found is not None
    assert found.session_id == session.session_id
    assert found.role == Role.OPERATOR


def test_validate_unknown_token_returns_none():
    """An unknown token returns None."""
    assert SessionStore().validate_token("does-not-exist") is None


def test_validate_empty_token_returns_none():
    """An empty token returns None."""
    assert SessionStore().validate_token("") is None


def test_validate_expired_token_returns_none():
    """An expired token returns None."""
    store = SessionStore()
    _session, token = store.create_session(Role.VIEWER)
    store._sessions[token].expires_at_utc = "1970-01-01T00:00:00+00:00"
    assert store.validate_token(token) is None


def test_invalidate_token_marks_inactive():
    """Invalidating a token makes it no longer valid."""
    store = SessionStore()
    _session, token = store.create_session(Role.OPERATOR)
    assert store.invalidate_token(token) is True
    assert store.validate_token(token) is None
    assert store.invalidate_token(token) is False


def test_invalidate_unknown_token_returns_false():
    """Invalidating an unknown token returns False."""
    assert SessionStore().invalidate_token("unknown-token") is False


def test_session_id_not_guessable_from_token():
    """The token is not derivable from the session ID and vice versa."""
    store = SessionStore()
    session, token = store.create_session(Role.OWNER)
    assert session.session_id != token
    assert "sess-" not in token


# --- Role-based authorization (unchanged, server-enforced) ----------------

def test_owner_can_change_settings():
    """Owner role is authorized to change sensitive settings."""
    assert SessionStore().can(Role.OWNER, "change_settings") is True


def test_operator_cannot_change_settings():
    """Operator role is not authorized to change sensitive settings."""
    assert SessionStore().can(Role.OPERATOR, "change_settings") is False


def test_viewer_cannot_change_settings():
    """Viewer role is not authorized to change sensitive settings."""
    assert SessionStore().can(Role.VIEWER, "change_settings") is False


def test_viewer_can_read_dashboard():
    """Viewer role is authorized to read dashboard state."""
    assert SessionStore().can(Role.VIEWER, "read_dashboard") is True


def test_operator_can_read_audit():
    """Operator role is authorized to read audit events."""
    assert SessionStore().can(Role.OPERATOR, "read_audit") is True


def test_viewer_cannot_read_audit():
    """Viewer role is not authorized to read audit events."""
    assert SessionStore().can(Role.VIEWER, "read_audit") is False


# --- Secret redaction (unchanged) -----------------------------------------

def test_secret_redacted_and_nonexportable():
    """redact_secret returns a redacted value that never exposes plaintext."""
    secret = "sk-live-1234567890abcdef"
    redacted = redact_secret(secret)
    assert redacted != secret
    assert secret not in redacted
    assert "****" in redacted


def test_redact_secret_empty():
    """Redacting an empty secret returns empty."""
    assert redact_secret("") == ""

def test_redact_secret_dummy_secret_not_exposed():
    """A dummy secret with surrounding context is never fully exposed."""
    secret = "superbot_dummy_secret_key_99xyz"
    redacted = redact_secret(secret)
    assert secret not in redacted
    assert len(redacted) < len(secret) + 4  # at most 4 visible chars + ****


# --- Localhost binding (unchanged) ----------------------------------------

def test_is_localhost_host_accepts_local():
    """Localhost variants are accepted as local binding."""
    for host in ("127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"):
        assert is_localhost_host(host) is True, f"{host} should be local"


def test_is_localhost_host_rejects_public():
    """Public/0.0.0.0 hosts are not local."""
    for host in ("0.0.0.0", "192.168.1.50", "example.com", "0.0.0.0:8000"):
        assert is_localhost_host(host) is False, f"{host} should not be local"


def test_validate_bind_host_accepts_localhost():
    """validate_bind_host does not raise for localhost."""
    validate_bind_host("127.0.0.1")
    validate_bind_host("localhost")


def test_validate_bind_host_rejects_public():
    """validate_bind_host raises for 0.0.0.0 or public hosts."""
    for host in ("0.0.0.0", "192.168.1.50", "example.com"):
        try:
            validate_bind_host(host)
        except ValueError:
            continue
        raise AssertionError(f"{host} should raise ValueError")


# --- Private VPN documentation (Phase 4.6) --------------------------------

def test_vpn_documents_localhost_only_binding():
    """VPN documentation states localhost-only binding requirement."""
    content = VPN_DOC_PATH.read_text(encoding="utf-8")
    assert "127.0.0.1" in content or "localhost" in content
    assert "0.0.0.0" in content
    assert "public" in content.lower()


def test_vpn_documents_private_vpn_requirement():
    """VPN documentation states remote access only via approved private VPN."""
    content = VPN_DOC_PATH.read_text(encoding="utf-8")
    assert "vpn" in content.lower()
    assert "private" in content.lower()
    assert "remote access" in content.lower()


def test_vpn_documents_no_public_exposure():
    """VPN documentation states no public exposure."""
    content = VPN_DOC_PATH.read_text(encoding="utf-8")
    normalized = " ".join(content.lower().split())
    assert "no public" in normalized
    assert "public exposure" in normalized or "public network" in normalized


def test_api_openapi_servers_localhost_only():
    """OpenAPI server URLs are localhost-only (no public exposure)."""
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    servers = response.json().get("servers", [])
    assert len(servers) >= 1
    for server in servers:
        url = server.get("url", "")
        assert "127.0.0.1" in url or "localhost" in url
        assert "0.0.0.0" not in url
        assert "public" not in url.lower()
