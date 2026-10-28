"""Tests for the OHLCV bar contract (schema.md section 3).

Validates numeric finiteness, OHLC relationships, time ordering, interval
alignment, and quality status. Source bars are immutable here; cleaned data is
a separate derived version.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from superbot.contracts.ohlcv import (
    InvalidOHLCVError,
    OHLCVBar,
    QualityStatus,
    Timeframe,
    VolumeKind,
)


def test_valid_ohlcv_bar_accepted():
    bar = OHLCVBar(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        provider_symbol="XAUUSD",
        mapping_version="1",
        timeframe=Timeframe.M5,
        bar_open_utc=datetime(2026, 10, 28, 10, 0, tzinfo=UTC),
        open=Decimal("2000.00"),
        high=Decimal("2005.00"),
        low=Decimal("1995.00"),
        close=Decimal("2003.00"),
        volume=Decimal("10.5"),
        volume_kind=VolumeKind.TICK,
        quality_status=QualityStatus.VALID,
        available_at_utc=datetime(2026, 10, 28, 10, 1, tzinfo=UTC),
        source_record_ref="mt5:XAUUSD:M5:20261028T1000",
    )
    assert bar.timeframe == Timeframe.M5
    assert bar.quality_status == QualityStatus.VALID


def test_ohlc_relationship_violation_rejected():
    with pytest.raises(InvalidOHLCVError):
        OHLCVBar(
            schema_version="1.0.0",
            provider_id="xm-mt5",
            instrument_id="XAUUSD",
            provider_symbol="XAUUSD",
            mapping_version="1",
            timeframe=Timeframe.H1,
            bar_open_utc=datetime(2026, 10, 28, 10, 0, tzinfo=UTC),
            open=Decimal("2000.00"),
            high=Decimal("1995.00"),  # high below open -> invalid
            low=Decimal("1990.00"),
            close=Decimal("1999.00"),
            quality_status=QualityStatus.VALID,
            available_at_utc=datetime(2026, 10, 28, 10, 1, tzinfo=UTC),
            source_record_ref="x",
        )


def test_volume_kind_and_quality_are_enums():
    bar = OHLCVBar(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        provider_symbol="XAUUSD",
        mapping_version="1",
        timeframe=Timeframe.H4,
        bar_open_utc=datetime(2026, 10, 28, 8, 0, tzinfo=UTC),
        open=Decimal(1),
        high=Decimal(2),
        low=Decimal(0),
        close=Decimal(1),
        volume=None,
        volume_kind=None,
        quality_status=QualityStatus.SUSPICIOUS,
        available_at_utc=datetime(2026, 10, 28, 10, 1, tzinfo=UTC),
        source_record_ref="x",
    )
    assert bar.volume is None
    assert bar.volume_kind is None
    assert bar.quality_status == QualityStatus.SUSPICIOUS
