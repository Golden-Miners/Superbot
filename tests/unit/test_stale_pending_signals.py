"""RED tests for M5.6 — Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests.

Tests define:
- PendingSignal: signal with entry time, expiry time, status (pending/filled/expired/cancelled)
- Stale signal: signal past expiry without fill = stale, blocks execution
- Signal expiry: signals expire after expiry timestamp; expired signals rejected
- Re-entry: after exit, can re-enter same symbol (not blocked forever)
- Same-symbol multi-strategy: multiple strategies can signal same symbol concurrently
- Opposite signal: opposite signal closes existing position before opening new one
- Versioned signal spec: SignalSpec carries schema_version, signal_id
- Deterministic: same inputs → same signal lifecycle
- No discretionary terms: all timestamps/thresholds explicit
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from superbot.strategy.stale_pending_signals import (
    PendingSignal,
    SignalExecutor,
    SignalSpec,
    SignalStatus,
    StaleSignalError,
    is_stale,
)


def test_pending_signal_creation():
    """PendingSignal created with pending status."""
    sig = PendingSignal(
        signal_id="sig_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 11, 1),
        expiry_ts=date(2026, 11, 5),
    )
    assert sig.signal_id == "sig_001"
    assert sig.symbol == "ESZ25"
    assert sig.side == "long"
    assert sig.status == SignalStatus.PENDING


def test_stale_signal_detected():
    """Signal past expiry without fill = stale."""
    sig = PendingSignal(
        signal_id="sig_stale_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    assert is_stale(sig, date(2026, 10, 20)) is True


def test_stale_signal_not_detected_before_expiry():
    """Signal before expiry is not stale."""
    sig = PendingSignal(
        signal_id="sig_fresh_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    assert is_stale(sig, date(2026, 10, 10)) is False


def test_stale_signal_at_expiry():
    """Signal at exact expiry is not stale (expiry is inclusive boundary)."""
    sig = PendingSignal(
        signal_id="sig_boundary_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    assert is_stale(sig, date(2026, 10, 15)) is False


def test_execute_stale_signal_blocked():
    """Executing a stale signal raises StaleSignalError."""
    executor = SignalExecutor()
    sig = PendingSignal(
        signal_id="sig_stale_exec_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    executor.register_signal(sig)
    with pytest.raises(StaleSignalError):
        executor.execute(sig, date(2026, 10, 20), Decimal("100.5"))


def test_execute_fresh_signal_ok():
    """Executing a fresh signal succeeds."""
    executor = SignalExecutor()
    sig = PendingSignal(
        signal_id="sig_fresh_exec_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    executor.register_signal(sig)
    result = executor.execute(sig, date(2026, 10, 10), Decimal("100.5"))
    assert sig.status == SignalStatus.FILLED
    assert result.entry_price == Decimal("100.5")


def test_re_entry_after_exit_allowed():
    """After exit, can re-enter same symbol."""
    executor = SignalExecutor()
    sig1 = PendingSignal(
        signal_id="sig_reentry_1",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 10),
    )
    sig2 = PendingSignal(
        signal_id="sig_reentry_2",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("105.0"),
        entry_ts=date(2026, 10, 11),
        expiry_ts=date(2026, 10, 20),
    )
    executor.register_signal(sig1)
    executor.execute(sig1, date(2026, 10, 5), Decimal("101.0"))
    executor.register_signal(sig2)
    result = executor.execute(sig2, date(2026, 10, 12), Decimal("105.5"))
    assert sig2.status == SignalStatus.FILLED
    assert result.entry_price == Decimal("105.5")


def test_same_symbol_multi_strategy():
    """Multiple strategies can signal same symbol concurrently."""
    executor = SignalExecutor()
    sig_a = PendingSignal(
        signal_id="sig_multi_a",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    sig_b = PendingSignal(
        signal_id="sig_multi_b",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("101.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    executor.register_signal(sig_a)
    executor.register_signal(sig_b)
    assert executor.get_signal("sig_multi_a") is sig_a
    assert executor.get_signal("sig_multi_b") is sig_b


def test_opposite_signal_closes_existing():
    """Opposite signal closes existing position before opening new one."""
    executor = SignalExecutor()
    sig_long = PendingSignal(
        signal_id="sig_opp_long",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    sig_short = PendingSignal(
        signal_id="sig_opp_short",
        symbol="ESZ25",
        side="short",
        entry_price=Decimal("105.0"),
        entry_ts=date(2026, 10, 8),
        expiry_ts=date(2026, 10, 20),
    )
    executor.register_signal(sig_long)
    executor.execute(sig_long, date(2026, 10, 2), Decimal("100.5"))
    # Opposite signal should close the long before opening short
    result = executor.execute_opposite(sig_short, date(2026, 10, 9), Decimal("104.5"))
    assert sig_long.status == SignalStatus.FILLED
    assert sig_short.status == SignalStatus.FILLED
    assert result.entry_price == Decimal("104.5")


def test_signal_spec_versioned():
    """SignalSpec carries schema_version and signal_id."""
    spec = SignalSpec(
        schema_version="1.0.0",
        signal_id="sig_spec_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    assert spec.schema_version == "1.0.0"
    assert spec.signal_id == "sig_spec_001"


def test_signal_status_enum():
    """SignalStatus enum has expected values."""
    assert SignalStatus.PENDING == "pending"
    assert SignalStatus.FILLED == "filled"
    assert SignalStatus.EXPIRED == "expired"
    assert SignalStatus.CANCELLED == "cancelled"


def test_deterministic_signal_lifecycle():
    """Same inputs produce identical signal lifecycle."""
    sig1 = PendingSignal(
        signal_id="sig_det_1",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 10),
    )
    sig2 = PendingSignal(
        signal_id="sig_det_1",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 10),
    )
    assert sig1 == sig2


def test_opposite_signal_no_existing_position():
    """Opposite signal with no existing position still opens new position."""
    executor = SignalExecutor()
    sig_short = PendingSignal(
        signal_id="sig_opp_no_long",
        symbol="ESZ25",
        side="short",
        entry_price=Decimal("105.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 15),
    )
    executor.register_signal(sig_short)
    result = executor.execute_opposite(sig_short, date(2026, 10, 2), Decimal("104.0"))
    assert sig_short.status == SignalStatus.FILLED
    assert result.entry_price == Decimal("104.0")


def test_expired_signal_marked_expired():
    """Signal past expiry not yet filled is marked expired."""
    executor = SignalExecutor()
    sig = PendingSignal(
        signal_id="sig_expire_001",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 5),
    )
    executor.register_signal(sig)
    executor.mark_expired(sig, date(2026, 10, 10))
    assert sig.status == SignalStatus.EXPIRED


def test_signal_expiry_before_entry():
    """Signal expires before any entry attempt is marked expired."""
    sig = PendingSignal(
        signal_id="sig_expire_before_entry",
        symbol="ESZ25",
        side="long",
        entry_price=Decimal("100.0"),
        entry_ts=date(2026, 10, 1),
        expiry_ts=date(2026, 10, 5),
    )
    assert is_stale(sig, date(2026, 10, 6)) is True
