"""RED tests for M6.1 — Chronological train/validation/untouched-test split and leakage audit.

Tests define:
- Chronological split: train = earliest bars, validation = middle, untouched-test = latest
- No overlap between splits (no duplicate timestamps across train/val/test)
- Gap between validation and test to prevent leakage
- Leakage detection: duplicate bars across splits = leakage error
- Leakage detection: future-dated data in training split = leakage error
- Split respects minimum sizes for each split
- Untouched test set never used in training or validation
- Deterministic: same inputs → same split
- Versioned split spec: SplitSpec carries schema_version, spec_id
- No discretionary terms: all ratios/timestamps explicit
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from superbot.data.chronological_split import (
    LeakageError,
    SplitSpec,
    audit_leakage,
    is_chronological,
    split_chronological,
)


def test_split_chronological_order():
    """Train bars all precede validation bars, which all precede test bars."""
    bars = [
        (date(2026, 1, 1), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (date(2026, 1, 2), Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (date(2026, 1, 3), Decimal("102.0"), Decimal("103.0"), Decimal("101.0"), Decimal("102.0")),
        (date(2026, 1, 4), Decimal("103.0"), Decimal("104.0"), Decimal("102.0"), Decimal("103.0")),
        (date(2026, 1, 5), Decimal("104.0"), Decimal("105.0"), Decimal("103.0"), Decimal("104.0")),
        (date(2026, 1, 6), Decimal("105.0"), Decimal("106.0"), Decimal("104.0"), Decimal("105.0")),
        (date(2026, 1, 7), Decimal("106.0"), Decimal("107.0"), Decimal("105.0"), Decimal("106.0")),
        (date(2026, 1, 8), Decimal("107.0"), Decimal("108.0"), Decimal("106.0"), Decimal("107.0")),
        (date(2026, 1, 9), Decimal("108.0"), Decimal("109.0"), Decimal("107.0"), Decimal("108.0")),
        (date(2026, 1, 10), Decimal("109.0"), Decimal("110.0"), Decimal("108.0"), Decimal("109.0")),
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_001",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    result = split_chronological(bars, spec)
    assert result.train_ts[-1] < result.val_ts[0]
    assert result.val_ts[-1] < result.test_ts[0]


def test_no_overlap_across_splits():
    """No timestamp appears in more than one split."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 11)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_no_overlap",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    result = split_chronological(bars, spec)
    all_ts = set(result.train_ts) | set(result.val_ts) | set(result.test_ts)
    assert len(all_ts) == len(result.train_ts) + len(result.val_ts) + len(result.test_ts)


def test_gap_between_val_and_test():
    """Gap bars separate validation from test (prevents leakage)."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 12)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_gap",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
    )
    result = split_chronological(bars, spec)
    # gap bars are between val end and test start
    assert len(result.train_ts) == 4
    assert len(result.val_ts) == 3
    assert len(result.test_ts) == 3
    assert len(result.gap_ts) == 1
    assert result.val_ts[-1] < result.gap_ts[0] < result.test_ts[0]


def test_insufficient_bars_raises():
    """Fewer bars than required raises ValueError."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 5)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_insuff",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    with pytest.raises(ValueError):
        split_chronological(bars, spec)


def test_minimum_split_sizes():
    """Each split meets its minimum size requirement."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 11)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_min",
        train_bars=3,
        val_bars=3,
        test_bars=3,
        gap_bars=1,
    )
    result = split_chronological(bars, spec)
    assert len(result.train_ts) >= 3
    assert len(result.val_ts) >= 3
    assert len(result.test_ts) >= 3


def test_untouched_test_not_in_training():
    """Test set bars never appear in training or validation."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 11)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_untouched",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    result = split_chronological(bars, spec)
    train_test_overlap = set(result.train_ts) & set(result.test_ts)
    val_test_overlap = set(result.val_ts) & set(result.test_ts)
    assert len(train_test_overlap) == 0
    assert len(val_test_overlap) == 0


def test_deterministic_split():
    """Same inputs yield identical split."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 11)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_det",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    r1 = split_chronological(bars, spec)
    r2 = split_chronological(bars, spec)
    assert r1.train_ts == r2.train_ts
    assert r1.val_ts == r2.val_ts
    assert r1.test_ts == r2.test_ts


def test_audit_leakage_no_overlap_passes():
    """No duplicate timestamps across splits passes audit."""
    bars = [
        (date(2026, 1, d), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0"))
        for d in range(1, 11)
    ]
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_audit_clean",
        train_bars=4,
        val_bars=3,
        test_bars=3,
        gap_bars=0,
    )
    result = split_chronological(bars, spec)
    audit_leakage(result.train_ts, result.val_ts, result.test_ts)  # should not raise


def test_audit_leakage_duplicate_across_splits():
    """Duplicate timestamp across train and test raises LeakageError."""
    train_ts = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    val_ts = [date(2026, 1, 4), date(2026, 1, 5)]
    test_ts = [date(2026, 1, 3), date(2026, 1, 6), date(2026, 1, 7)]  # 2026-01-03 duplicated
    with pytest.raises(LeakageError):
        audit_leakage(train_ts, val_ts, test_ts)


def test_audit_leakage_future_data_in_train():
    """Future-dated data in training split raises LeakageError."""
    train_ts = [date(2026, 1, 5), date(2026, 1, 6)]
    val_ts = [date(2026, 1, 1), date(2026, 1, 2)]
    test_ts = [date(2026, 1, 3), date(2026, 1, 4)]
    with pytest.raises(LeakageError):
        audit_leakage(train_ts, val_ts, test_ts)


def test_split_spec_versioned():
    """SplitSpec carries schema_version and spec_id."""
    spec = SplitSpec(
        schema_version="1.0.0",
        spec_id="split_ver_001",
        train_bars=10,
        val_bars=5,
        test_bars=5,
        gap_bars=2,
    )
    assert spec.schema_version == "1.0.0"
    assert spec.spec_id == "split_ver_001"


def test_is_chronological_ordered():
    """Bars sorted by ascending timestamp are chronological."""
    bars = [
        (date(2026, 1, 1), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (date(2026, 1, 2), Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
        (date(2026, 1, 3), Decimal("102.0"), Decimal("103.0"), Decimal("101.0"), Decimal("102.0")),
    ]
    assert is_chronological(bars) is True


def test_is_chronological_unordered():
    """Bars not sorted by ascending timestamp are not chronological."""
    bars = [
        (date(2026, 1, 3), Decimal("102.0"), Decimal("103.0"), Decimal("101.0"), Decimal("102.0")),
        (date(2026, 1, 1), Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (date(2026, 1, 2), Decimal("101.0"), Decimal("102.0"), Decimal("100.0"), Decimal("101.0")),
    ]
    assert is_chronological(bars) is False
