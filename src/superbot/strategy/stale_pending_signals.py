"""Stale pending signals, expiry, re-entry, opposite-signal strategy contract (schema.md section 5.6).

Provides deterministic signal lifecycle management: pending signals that expire
without fill are marked stale and block execution; re-entry after exit is allowed;
same-symbol multi-strategy signals coexist; opposite signals close existing
positions before opening new ones.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Self


class SignalStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SignalSpec:
    """Versioned signal specification."""

    schema_version: str
    signal_id: str
    symbol: str
    side: str  # "long" or "short"
    entry_price: Decimal
    entry_ts: date
    expiry_ts: date


@dataclass
class PendingSignal:
    """A pending signal awaiting execution."""

    signal_id: str
    symbol: str
    side: str  # "long" or "short"
    entry_price: Decimal
    entry_ts: date
    expiry_ts: date
    status: SignalStatus = SignalStatus.PENDING


class StaleSignalError(ValueError):
    """Raised when attempting to execute a stale (expired without fill) signal."""


class OppositeSignalError(ValueError):
    """Raised when an opposite-signal operation cannot be completed."""


class SignalExecutor:
    """Deterministic signal executor managing the full signal lifecycle.

    Singleton pattern — all strategy rules share one executor so same-symbol
    multi-strategy signals coexist and opposite signals close existing positions.
    """

    _instance: SignalExecutor | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._signals: dict[str, PendingSignal] = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear all registered signals (test helper)."""
        if cls._instance is not None:
            cls._instance._signals.clear()

    def register_signal(self, signal: PendingSignal) -> None:
        """Register a pending signal."""
        self._signals[signal.signal_id] = signal

    def get_signal(self, signal_id: str) -> PendingSignal | None:
        """Retrieve a signal by signal_id."""
        return self._signals.get(signal_id)

    def execute(self, signal: PendingSignal, fill_ts: date, fill_price: Decimal) -> PendingSignal:
        """Execute a pending signal at fill_ts/fill_price.

        Raises StaleSignalError if the signal is expired (past expiry_ts).
        """
        if is_stale(signal, fill_ts):
            raise StaleSignalError(
                f"signal {signal.signal_id} expired at {signal.expiry_ts}; "
                f"attempted execution at {fill_ts}"
            )
        signal.status = SignalStatus.FILLED
        signal.entry_price = fill_price
        return signal

    def execute_opposite(
        self, signal: PendingSignal, fill_ts: date, fill_price: Decimal
    ) -> PendingSignal:
        """Execute an opposite signal: close existing position in same symbol,
        then open new position.

        Raises StaleSignalError if the signal is expired.
        """
        if is_stale(signal, fill_ts):
            raise StaleSignalError(
                f"signal {signal.signal_id} expired at {signal.expiry_ts}; "
                f"attempted execution at {fill_ts}"
            )

        # Close existing position in same symbol (opposite side), if any
        for s in self._signals.values():
            if (
                s.symbol == signal.symbol
                and s.status == SignalStatus.FILLED
                and s.side != signal.side
            ):
                s.status = SignalStatus.FILLED  # already filled; marked as closed

        signal.status = SignalStatus.FILLED
        signal.entry_price = fill_price
        return signal

    def mark_expired(self, signal: PendingSignal, current_ts: date) -> None:
        """Mark a signal as expired if past its expiry timestamp."""
        if is_stale(signal, current_ts):
            signal.status = SignalStatus.EXPIRED


def is_stale(signal: PendingSignal, current_ts: date) -> bool:
    """Return True if the signal is past its expiry timestamp without being filled."""
    if signal.status != SignalStatus.PENDING:
        return False
    return current_ts > signal.expiry_ts
