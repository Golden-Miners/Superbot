"""Instrument specification contract (schema.md section 2).

Null fields mean absent, never zero. Missing/stale fields required for
simulation or sizing must block that operation at the call site; this module
preserves nulls and never substitutes broker-typical values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class AssetClass(str, Enum):
    METAL = "metal"
    CRYPTO = "crypto"
    ENERGY = "energy"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class InvalidInstrumentError(ValueError):
    """Raised when an instrument specification fails validation."""


# Decimal fields that must remain null-or-decimal (never coerced to zero).
_DECIMAL_FIELDS = (
    "contract_size",
    "tick_size",
    "tick_value",
    "volume_min",
    "volume_max",
    "volume_step",
)


@dataclass(frozen=True)
class InstrumentSpec:
    """Discovered, verified instrument metadata. Never guessed."""

    schema_version: str
    instrument_id: str
    provider_id: str
    provider_symbol: str
    asset_class: AssetClass
    quote_currency: str | None = None
    base_currency: str | None = None
    contract_size: Decimal | None = None
    tick_size: Decimal | None = None
    tick_value: Decimal | None = None
    volume_min: Decimal | None = None
    volume_max: Decimal | None = None
    volume_step: Decimal | None = None
    price_precision: int | None = None
    volume_precision: int | None = None
    trade_sessions_ref: str | None = None
    server_timezone: str | None = None
    source_updated_at_utc: str | None = None
    verified_at_utc: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNAVAILABLE
    source_metadata_ref: str = ""

    def __post_init__(self) -> None:
        self._validate_required()
        self._validate_decimals()
        self._validate_enums()
        self._validate_precision()

    def _validate_required(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise InvalidInstrumentError("schema_version is required")
        if not isinstance(self.instrument_id, str) or not self.instrument_id:
            raise InvalidInstrumentError("instrument_id is required")
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise InvalidInstrumentError("provider_id is required")
        if not isinstance(self.provider_symbol, str) or not self.provider_symbol:
            raise InvalidInstrumentError("provider_symbol is required")
        if not isinstance(self.source_metadata_ref, str) or not self.source_metadata_ref:
            raise InvalidInstrumentError("source_metadata_ref is required")

    def _validate_decimals(self) -> None:
        for name in _DECIMAL_FIELDS:
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, Decimal):
                raise InvalidInstrumentError(f"{name} must be Decimal or null, got {value!r}")

    def _validate_enums(self) -> None:
        if not isinstance(self.asset_class, AssetClass):
            raise InvalidInstrumentError(
                f"asset_class must be one of {[c.value for c in AssetClass]}"
            )
        if not isinstance(self.verification_status, VerificationStatus):
            raise InvalidInstrumentError(
                f"verification_status must be one of {[s.value for s in VerificationStatus]}"
            )

    def _validate_precision(self) -> None:
        for name in ("price_precision", "volume_precision"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise InvalidInstrumentError(f"{name} must be a non-negative int or null")
