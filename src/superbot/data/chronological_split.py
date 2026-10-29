"""Chronological train/validation/untouched-test split and leakage audit (schema.md section 6.1).

Splits OHLCV bar data chronologically: train = earliest bars, validation = middle,
untouched-test = latest bars. Enforces a gap between validation and test to prevent
leakage, and audits splits for duplicate timestamps (cross-split leakage) and
future-dated data in training (look-ahead leakage).

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class LeakageError(ValueError):
    """Raised when data leakage is detected across train/validation/test splits."""


@dataclass(frozen=True)
class SplitSpec:
    """Versioned chronological split specification."""

    schema_version: str
    spec_id: str
    train_bars: int
    val_bars: int
    test_bars: int
    gap_bars: int


@dataclass(frozen=True)
class SplitResult:
    """Result of a chronological split: timestamp lists per split."""

    train_ts: list[date]
    val_ts: list[date]
    test_ts: list[date]
    gap_ts: list[date]


def is_chronological(
    bars: list[tuple[date, Decimal, Decimal, Decimal, Decimal]],
) -> bool:
    """Return True if bars are sorted by ascending timestamp."""
    for i in range(1, len(bars)):
        if bars[i][0] <= bars[i - 1][0]:
            return False
    return True


def split_chronological(
    bars: list[tuple[date, Decimal, Decimal, Decimal, Decimal]],
    spec: SplitSpec,
) -> SplitResult:
    """Split bars chronologically into train/validation/test with an optional gap.

    Train = earliest bars, validation = middle, test = latest bars.
    Gap bars sit between validation and test to prevent leakage.

    Raises ValueError if bars are not chronological or insufficient bars.
    """
    if not is_chronological(bars):
        raise ValueError("bars must be sorted by ascending timestamp")

    total_needed = spec.train_bars + spec.val_bars + spec.test_bars + spec.gap_bars
    if len(bars) < total_needed:
        raise ValueError(f"insufficient bars: {len(bars)} < required {total_needed}")

    train_ts = [bars[i][0] for i in range(spec.train_bars)]
    val_start = spec.train_bars
    val_end = val_start + spec.val_bars
    val_ts = [bars[i][0] for i in range(val_start, val_end)]
    gap_start = val_end
    gap_end = gap_start + spec.gap_bars
    gap_ts = [bars[i][0] for i in range(gap_start, gap_end)]
    test_start = gap_end
    test_end = test_start + spec.test_bars
    test_ts = [bars[i][0] for i in range(test_start, test_end)]

    return SplitResult(
        train_ts=train_ts,
        val_ts=val_ts,
        test_ts=test_ts,
        gap_ts=gap_ts,
    )


def audit_leakage(
    train_ts: list[date],
    val_ts: list[date],
    test_ts: list[date],
) -> None:
    """Audit splits for leakage.

    Raises LeakageError if:
    - Any timestamp appears in more than one split (duplicate across train/val/test)
    - Any training timestamp is newer than any validation/test timestamp
      (future-dated data in training = look-ahead leakage)
    """
    all_ts: list[date] = []
    all_ts.extend(train_ts)
    all_ts.extend(val_ts)
    all_ts.extend(test_ts)
    if len(all_ts) != len(set(all_ts)):
        raise LeakageError("duplicate timestamp across train/validation/test splits")

    if train_ts and (val_ts or test_ts):
        latest_train = max(train_ts)
        earliest_val_test = min([ts for ts in (val_ts + test_ts) if ts])
        if latest_train > earliest_val_test:
            raise LeakageError(
                f"training data contains future-dated timestamp {latest_train}; "
                f"earliest val/test timestamp is {earliest_val_test}"
            )
