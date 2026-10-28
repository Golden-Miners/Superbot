"""OHLCV bar contract (schema.md section 3).

Validates numeric finiteness, OHLC relationships, time ordering, interval
alignment, and quality status. Source bars are immutable here; repaired or
cleaned data is a separate derived version with provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum


class Timeframe(str, Enum):
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"


_TIMEFRAME_DELTA = {
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
}


class VolumeKind(str, Enum):
    TICK = "tick"
    REAL = "real"
    UNKNOWN = "unknown"


class QualityStatus(str, Enum):
    VALID = "valid"
    GAP_ADJACENT = "gap_adjacent"
    SUSPICIOUS = "suspicious"
    INVALID = "invalid"
    STALE = "stale"


class InvalidOHLCVError(ValueError):
    """Raised when an OHLCV bar fails validation."""


@dataclass(frozen=True)
class OHLCVBar:
    """A single source-stamped OHLCV bar. Immutable after validation."""

    schema_version: str
    provider_id: str
    instrument_id: str
    provider_symbol: str
    mapping_version: str
    timeframe: Timeframe
    bar_open_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    volume_kind: VolumeKind | None = None
    bar_close_utc: datetime | None = None
    source_timestamp: str | None = None
    source_timezone: str | None = None
    source_revision: str | None = None
    quality_status: QualityStatus = QualityStatus.VALID
    available_at_utc: datetime | None = None
    source_record_ref: str = ""

    def __post_init__(self) -> None:
        self._validate_required()
        self._validate_decimals()
        self._validate_enums()
        self._validate_ohlc_relationships()
        self._validate_time()
        self._validate_interval_alignment()
        self._validate_availability()

    def _validate_required(self) -> None:
        for name in (
            "schema_version",
            "provider_id",
            "instrument_id",
            "provider_symbol",
            "mapping_version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise InvalidOHLCVError(f"{name} is required")

    def _validate_decimals(self) -> None:
        for name in ("open", "high", "low", "close"):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise InvalidOHLCVError(f"{name} must be Decimal")
            if not value.is_finite():
                raise InvalidOHLCVError(f"{name} must be finite")
        if self.volume is not None and (
            not isinstance(self.volume, Decimal) or not self.volume.is_finite()
        ):
            raise InvalidOHLCVError("volume must be Decimal or null")

    def _validate_enums(self) -> None:
        if not isinstance(self.timeframe, Timeframe):
            raise InvalidOHLCVError(f"timeframe must be one of {[t.value for t in Timeframe]}")
        if self.volume_kind is not None and not isinstance(self.volume_kind, VolumeKind):
            raise InvalidOHLCVError(
                f"volume_kind must be one of {[v.value for v in VolumeKind]} or null"
            )
        if not isinstance(self.quality_status, QualityStatus):
            raise InvalidOHLCVError(
                f"quality_status must be one of {[q.value for q in QualityStatus]}"
            )

    def _validate_ohlc_relationships(self) -> None:
        lo = min(self.open, self.close)
        hi = max(self.open, self.close)
        if not (self.low <= lo <= hi <= self.high):
            raise InvalidOHLCVError(
                f"OHLC relationship violated: low={self.low} "
                f"<= min(open,close)={lo} <= max(open,close)={hi} "
                f"<= high={self.high}"
            )

    def _validate_time(self) -> None:
        if not isinstance(self.bar_open_utc, datetime):
            raise InvalidOHLCVError("bar_open_utc is required")
        if self.bar_close_utc is not None and self.bar_close_utc <= self.bar_open_utc:
            raise InvalidOHLCVError("bar_close_utc must be after bar_open_utc")

    def _validate_interval_alignment(self) -> None:
        delta = _TIMEFRAME_DELTA[self.timeframe]
        epoch = datetime(1970, 1, 1, tzinfo=UTC)
        offset = (self.bar_open_utc - epoch) % delta
        if offset != timedelta(0):
            raise InvalidOHLCVError(
                f"bar_open_utc {self.bar_open_utc} is not aligned to {self.timeframe}"
            )

    def _validate_availability(self) -> None:
        if self.available_at_utc is None:
            raise InvalidOHLCVError("available_at_utc is required")
