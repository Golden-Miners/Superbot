"""RED tests for M2.2 data-quality validation (synthetic fixtures).

These tests define the expected behaviour before any implementation exists:
chronology, duplicates, gaps, staleness, suspicious prices, and availability
timestamps are all validated on collections of OHLCV bars.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from superbot.contracts.ohlcv import (
    InvalidOHLCVError,
    OHLCVBar,
    QualityStatus,
    Timeframe,
    VolumeKind,
)

# Base timestamp aligned to M5 (2026-10-28 10:00:00 UTC).
BASE = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
BASE_TS = int(BASE.timestamp())


def _bar(
    offset_seconds: int,
    open_px: str,
    high: str,
    low: str,
    close: str,
    quality: QualityStatus = QualityStatus.VALID,
) -> OHLCVBar:
    ts = BASE_TS + offset_seconds
    return OHLCVBar(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        provider_symbol="XAUUSD",
        mapping_version="1",
        timeframe=Timeframe.M5,
        bar_open_utc=datetime.fromtimestamp(ts, tz=UTC),
        open=Decimal(open_px),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(1),
        volume_kind=VolumeKind.TICK,
        quality_status=quality,
        available_at_utc=datetime.fromtimestamp(ts, tz=UTC),
        source_record_ref=f"mt5:XAUUSD:M5:{ts}",
    )


def test_chronology_violations_are_rejected():
    from superbot.data.quality import validate_chronology

    bars = [
        _bar(0, "100", "101", "99", "100"),
        _bar(-300, "99", "100", "98", "99"),  # goes backwards
    ]
    with pytest.raises(InvalidOHLCVError):
        validate_chronology(bars)


def test_duplicate_timestamps_are_rejected():
    from superbot.data.quality import validate_no_duplicates

    bars = [
        _bar(0, "100", "101", "99", "100"),
        _bar(0, "100", "101", "99", "100"),  # duplicate open time
    ]
    with pytest.raises(InvalidOHLCVError):
        validate_no_duplicates(bars)


def test_gaps_are_flagged_but_do_not_reject():
    from superbot.data.quality import validate_gaps

    bars = [
        _bar(0, "100", "101", "99", "100"),
        _bar(35 * 60, "101", "102", "100", "101"),  # 35 min gap on M5
    ]
    report = validate_gaps(bars, Timeframe.M5)
    assert report.has_gaps is True
    assert len(report.gaps) == 1


def test_stale_bars_are_flagged():
    from superbot.data.quality import validate_freshness

    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    bar = _bar(0, "100", "101", "99", "100")
    bar = OHLCVBar(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        instrument_id="XAUUSD",
        provider_symbol="XAUUSD",
        mapping_version="1",
        timeframe=Timeframe.M5,
        bar_open_utc=bar.bar_open_utc,
        open=Decimal(100),
        high=Decimal(101),
        low=Decimal(99),
        close=Decimal(100),
        volume=Decimal(1),
        volume_kind=VolumeKind.TICK,
        quality_status=QualityStatus.VALID,
        available_at_utc=now - timedelta(hours=25),  # stale (>24h)
        source_record_ref="mt5:XAUUSD:M5:1727479200",
    )
    report = validate_freshness([bar], max_age=timedelta(hours=24), now=now)
    assert report.is_stale is True


def test_suspicious_prices_are_flagged():
    from superbot.data.quality import validate_prices

    bars = [
        _bar(0, "0", "0", "0", "0"),  # zero prices -> suspicious, OHLC-valid
    ]
    report = validate_prices(bars)
    assert report.has_suspicious is True
    assert len(report.suspicious) == 1


def test_availability_timestamps_are_required():
    # OHLCVBar enforces availability at construction (schema.md section 3).
    # validate_availability is a collection-level belt-and-suspenders check.
    with pytest.raises(InvalidOHLCVError):
        OHLCVBar(
            schema_version="1.0.0",
            provider_id="xm-mt5",
            instrument_id="XAUUSD",
            provider_symbol="XAUUSD",
            mapping_version="1",
            timeframe=Timeframe.M5,
            bar_open_utc=BASE,
            open=Decimal(100),
            high=Decimal(101),
            low=Decimal(99),
            close=Decimal(100),
            volume=Decimal(1),
            volume_kind=VolumeKind.TICK,
            quality_status=QualityStatus.VALID,
            available_at_utc=None,
            source_record_ref="mt5:XAUUSD:M5:1727479200",
        )
