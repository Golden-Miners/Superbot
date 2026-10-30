"""M11.3 — Auth sessions, roles, redaction, local binding, private VPN docs.

Deterministic auth service:
- SessionStore: create, validate (with expiry), invalidate sessions keyed by role
- Role-based access control: backend enforces authorization for actions
- Secret redaction: secrets masked, never exported in plaintext
- Localhost-only binding enforcement: rejects 0.0.0.0 / public hosts
- VPN_DOC_PATH: path to private VPN documentation (remote access only via
  approved private VPN)

Stdlib-only; no import-time network/database activity; no public binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path


class Role(str, Enum):
    """Access roles. Backend enforces authorization per action."""

    OWNER = "owner"
    OPERATOR = "operator"
    VIEWER = "viewer"


SESSION_TTL = timedelta(hours=8)


@dataclass
class Session:
    """An authenticated session bound to a role."""

    session_id: str
    role: Role
    created_at_utc: str
    expires_at_utc: str
    is_active: bool = True


@dataclass
class SessionStore:
    """In-memory session store with role-based authorization checks.

    Sessions expire after SESSION_TTL. Validation is a pure predicate on the
    stored session (no side effects).
    """

    _sessions: dict[str, Session] = field(default_factory=dict)
    _counter: int = field(default=0)

    def create_session(self, role: Role) -> Session:
        """Create a new active session for the given role."""
        self._counter += 1
        now = datetime.now(tz=UTC)
        expires = now + SESSION_TTL
        session = Session(
            session_id=f"sess-{self._counter}",
            role=role,
            created_at_utc=now.isoformat(),
            expires_at_utc=expires.isoformat(),
            is_active=True,
        )
        self._sessions[session.session_id] = session
        return session

    def validate_session(self, session_id: str) -> Session | None:
        """Return the session if active and not expired, else None."""
        session = self._sessions.get(session_id)
        if session is None or not session.is_active:
            return None
        try:
            expires = datetime.fromisoformat(session.expires_at_utc)
        except ValueError:
            return None
        if expires <= datetime.now(tz=UTC):
            return None
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Mark a session inactive. Returns True if a session was invalidated."""
        session = self._sessions.get(session_id)
        if session is None or not session.is_active:
            return False
        session.is_active = False
        return True

    def can(self, role: Role, action: str) -> bool:
        """Backend authorization: is the role allowed to perform the action?

        Enforced on the server; hiding a UI button is insufficient.
        """
        if action == "change_settings":
            return role == Role.OWNER
        if action in ("read_dashboard", "read_health", "read_data_explorer"):
            return role in (Role.OWNER, Role.OPERATOR, Role.VIEWER)
        if action in ("read_audit", "cancel_job", "update_strategy"):
            return role in (Role.OWNER, Role.OPERATOR)
        return False


def redact_secret(value: str) -> str:
    """Return a redacted form of a secret that never exposes the plaintext."""
    if not value:
        return ""
    visible = min(4, len(value))
    return f"****{value[-visible:]}" if visible else "****"


def is_localhost_host(host: str) -> bool:
    """Return True if host is a localhost/loopback binding candidate."""
    if not host:
        return False
    host = host.split("://", 1)[-1]
    lowered = host.lower()
    localhost_names = {
        "127.0.0.1",
        "localhost",
        "::1",
        "0:0:0:0:0:0:0:1",
        "0000:0000:0000:0000:0000:0000:0000:0001",
    }
    if lowered in localhost_names:
        return True
    # Strip an optional port (IPv4-style host:port). IPv6 loopback forms are
    # matched above before any splitting.
    if ":" in lowered:
        host_part = lowered.split(":", 1)[0]
        if host_part in localhost_names:
            return True
    return False


def validate_bind_host(host: str) -> None:
    """Raise ValueError if host is not a localhost-only bind address."""
    if not is_localhost_host(host):
        raise ValueError(
            f"Bind host must be localhost-only for local-first operation, got: {host}"
        )


# Path to the private VPN documentation. Remote access to the dashboard is only
# permitted through an approved private VPN; there is no public exposure.
VPN_DOC_PATH = Path("docs/private-vpn-access.md")

__all__ = [
    "SESSION_TTL",
    "VPN_DOC_PATH",
    "Role",
    "Session",
    "SessionStore",
    "is_localhost_host",
    "redact_secret",
    "validate_bind_host",
]
