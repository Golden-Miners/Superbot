"""Session/timezone boundary validation (M2.4).

Session boundaries and server timezone are explicit and never assumed.
Unknown timezone/session state is represented as SessionTimezoneState.UNKNOWN
and blocks affected work rather than defaulting to UTC or local time.
UTC canonical timestamps are preserved; provider/broker timezone metadata is
retained separately.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SessionTimezoneState(str, Enum):
    VERIFIED = "verified"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class UnknownTimezoneError(ValueError):
    """Raised when a session check requires an unknown server timezone."""


class SessionBoundaryError(ValueError):
    """Raised when a bar falls outside the configured trading session."""


@dataclass(frozen=True)
class SessionValidator:
    """Validates bar open times against a configured trading session.

    server_timezone is the broker/server timezone (e.g. XM server time). When
    None, the timezone is unknown and session checks raise UnknownTimezoneError
    instead of assuming a value.
    """

    provider_id: str
    instrument_id: str
    server_timezone: str | None = None
    session_open_utc: datetime | None = None
    session_close_utc: datetime | None = None
    state: SessionTimezoneState = SessionTimezoneState.UNKNOWN

    def __post_init__(self) -> None:
        # A verified/stale state requires a known timezone and session bounds.
        if self.state in (SessionTimezoneState.VERIFIED, SessionTimezoneState.STALE) and (
            self.server_timezone is None
            or self.session_open_utc is None
            or self.session_close_utc is None
        ):
            object.__setattr__(self, "state", SessionTimezoneState.UNKNOWN)
        elif self.state == SessionTimezoneState.UNKNOWN and (
            self.server_timezone is not None
            and self.session_open_utc is not None
            and self.session_close_utc is not None
        ):
            object.__setattr__(self, "state", SessionTimezoneState.VERIFIED)

    def is_within_session(self, bar_open_utc: datetime) -> bool:
        """Return True if bar_open_utc falls within the trading session.

        Raises UnknownTimezoneError when the server timezone/session is
        unknown — never assumes a timezone.
        """
        if self.state == SessionTimezoneState.UNKNOWN:
            raise UnknownTimezoneError(
                f"server timezone/session unknown for {self.provider_id}:{self.instrument_id}; "
                "cannot determine session membership without verified broker time"
            )
        if self.session_open_utc is None or self.session_close_utc is None:
            raise UnknownTimezoneError(
                f"session bounds unset for {self.provider_id}:{self.instrument_id}"
            )
        return self.session_open_utc <= bar_open_utc <= self.session_close_utc


def validate_session_boundaries(
    bars: Iterable[dict],
    session_open_utc: datetime,
    session_close_utc: datetime,
) -> None:
    """Reject any bar whose open time falls outside the session.

    Each bar dict must contain a timezone-aware 'bar_open_utc' datetime.
    """
    for bar in bars:
        bar_open = bar["bar_open_utc"]
        if not isinstance(bar_open, datetime) or bar_open.tzinfo is None:
            raise SessionBoundaryError(
                f"bar_open_utc must be a timezone-aware datetime, got {bar_open!r}"
            )
        if not (session_open_utc <= bar_open <= session_close_utc):
            raise SessionBoundaryError(
                f"bar at {bar_open} is outside session [{session_open_utc}, {session_close_utc}]"
            )
