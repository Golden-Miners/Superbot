"""RED tests for M11.3 — Auth sessions, roles, redaction, local binding.

Covers: session create/validate/expire/invalidate, role-based access control
(owner/operator/viewer), secret redaction, localhost-only binding enforcement,
and private VPN documentation requirement.

Acceptance: backend enforces authorization (hiding a button is insufficient),
no public network binding, secrets redacted and non-exportable, remote access
only through approved private VPN.
"""

from __future__ import annotations

from superbot.m11.auth import (
    Role,
    Session,
    SessionStore,
    is_localhost_host,
    redact_secret,
    validate_bind_host,
)


def test_role_enum_values():
    """Roles are owner, operator, viewer."""
    assert Role.OWNER == "owner"
    assert Role.OPERATOR == "operator"
    assert Role.VIEWER == "viewer"


def test_session_create_and_validate():
    """Creating a session yields an active session that validates."""
    store = SessionStore()
    session = store.create_session(Role.OWNER)
    assert isinstance(session, Session)
    assert session.role == Role.OWNER
    assert session.is_active is True
    assert session.session_id
    assert session.created_at_utc
    assert session.expires_at_utc

    found = store.validate_session(session.session_id)
    assert found is not None
    assert found.session_id == session.session_id


def test_session_expires_and_is_no_longer_valid():
    """An expired session returns None from validate_session."""
    store = SessionStore()
    session = store.create_session(Role.VIEWER)
    # Force expiry in the past.
    store._sessions[session.session_id].expires_at_utc = "1970-01-01T00:00:00+00:00"
    assert store.validate_session(session.session_id) is None


def test_session_invalidate():
    """Invalidating a session makes it no longer valid."""
    store = SessionStore()
    session = store.create_session(Role.OPERATOR)
    assert store.invalidate_session(session.session_id) is True
    assert store.validate_session(session.session_id) is None
    assert store.invalidate_session(session.session_id) is False


def test_unknown_session_returns_none():
    """Validating an unknown session id returns None."""
    assert SessionStore().validate_session("does-not-exist") is None


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


def test_secret_redacted_and_nonexportable():
    """redact_secret returns a redacted value that does not expose the secret."""
    secret = "sk-live-1234567890abcdef"
    redacted = redact_secret(secret)
    assert redacted != secret
    assert secret not in redacted
    assert "REDACTED" in redacted.upper() or "****" in redacted


def test_redact_secret_empty():
    """Redacting an empty secret returns empty."""
    assert redact_secret("") == ""


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


def test_vpn_documentation_exists():
    """Private VPN documentation is present (remote access only via approved VPN)."""
    from superbot.m11.auth import VPN_DOC_PATH

    assert VPN_DOC_PATH is not None
    content = VPN_DOC_PATH.read_text(encoding="utf-8")
    assert "vpn" in content.lower()
    assert "private" in content.lower()
    assert "remote access" in content.lower()
