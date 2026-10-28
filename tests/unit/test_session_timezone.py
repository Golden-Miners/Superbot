"""RED tests for M2.4 session/timezone boundary validation.

Session boundaries and server timezone are explicit and never assumed.
Unknown timezone/session state blocks affected work.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from superbot.data.session import (
    SessionBoundaryError,
    SessionTimezoneState,
    SessionValidator,
    UnknownTimezoneError,
    validate_session_boundaries,
)


def test_valid_session_aligned_bars_accepted():
    validator = SessionValidator(
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        server_timezone="UTC",
        session_open_utc=datetime(2026, 10, 28, 0, 0, tzinfo=UTC),
        session_close_utc=datetime(2026, 10, 28, 23, 59, tzinfo=UTC),
    )
    bar_open = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
    assert validator.is_within_session(bar_open) is True


def test_bar_outside_session_flagged():
    validator = SessionValidator(
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        server_timezone="UTC",
        session_open_utc=datetime(2026, 10, 28, 0, 0, tzinfo=UTC),
        session_close_utc=datetime(2026, 10, 28, 6, 0, tzinfo=UTC),
    )
    bar_open = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
    assert validator.is_within_session(bar_open) is False


def test_unknown_timezone_is_explicit_not_assumed():
    validator = SessionValidator(
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        server_timezone=None,  # unknown
        session_open_utc=None,
        session_close_utc=None,
    )
    assert validator.state == SessionTimezoneState.UNKNOWN
    with pytest.raises(UnknownTimezoneError):
        validator.is_within_session(datetime(2026, 10, 28, 10, 0, tzinfo=UTC))


def test_validate_session_boundaries_rejects_outside_session():
    bars = [
        {"bar_open_utc": datetime(2026, 10, 28, 10, 0, tzinfo=UTC)},
    ]
    with pytest.raises(SessionBoundaryError):
        validate_session_boundaries(
            bars,
            session_open_utc=datetime(2026, 10, 28, 0, 0, tzinfo=UTC),
            session_close_utc=datetime(2026, 10, 28, 6, 0, tzinfo=UTC),
        )


def test_utc_canonical_preserved_with_provider_timezone():
    # Canonical bar_open_utc stays UTC; provider timezone metadata separate.
    from datetime import timezone as tz

    kolkata = tz(timedelta(hours=5, minutes=30))
    provider_open = datetime(2026, 10, 28, 15, 30, tzinfo=kolkata)
    assert provider_open.utcoffset() == timedelta(hours=5, minutes=30)
    utc_open = provider_open.astimezone(UTC)
    assert utc_open == datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
