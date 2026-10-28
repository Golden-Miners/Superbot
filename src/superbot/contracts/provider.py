"""Provider/source metadata contract (M2.1).

Represents a market-data provider (e.g. XM MT5) with its own identity,
discovery/provenance metadata and verification status. Unknown or missing
metadata is preserved explicitly; broker-typical values are never substituted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    MT5 = "mt5"
    CSV = "csv"
    API = "api"
    UNKNOWN = "unknown"


class ProviderVerificationStatus(str, Enum):
    VERIFIED = "verified"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class InvalidProviderError(ValueError):
    """Raised when a provider specification fails validation."""


@dataclass(frozen=True)
class ProviderSpec:
    """Discovered provider/source metadata and provenance. Never guessed."""

    schema_version: str
    provider_id: str
    provider_name: str | None = None
    provider_type: ProviderType = ProviderType.UNKNOWN
    source_metadata_ref: str | None = None
    discovered_at_utc: datetime | None = None
    verification_status: ProviderVerificationStatus = ProviderVerificationStatus.UNAVAILABLE
    verified_at_utc: datetime | None = None
    read_only: bool = False

    def __post_init__(self) -> None:
        self._validate_required()
        self._validate_enums()
        self._validate_times()

    def _validate_required(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise InvalidProviderError("schema_version is required")
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise InvalidProviderError("provider_id is required")
        if self.source_metadata_ref is not None and (
            not isinstance(self.source_metadata_ref, str) or not self.source_metadata_ref
        ):
            raise InvalidProviderError("source_metadata_ref must be a non-empty string or null")

    def _validate_enums(self) -> None:
        if not isinstance(self.provider_type, ProviderType):
            raise InvalidProviderError(
                f"provider_type must be one of {[t.value for t in ProviderType]}"
            )
        if not isinstance(self.verification_status, ProviderVerificationStatus):
            raise InvalidProviderError(
                f"verification_status must be one of "
                f"{[s.value for s in ProviderVerificationStatus]}"
            )

    def _validate_times(self) -> None:
        for name, value in (
            ("discovered_at_utc", self.discovered_at_utc),
            ("verified_at_utc", self.verified_at_utc),
        ):
            if value is not None and not isinstance(value, datetime):
                raise InvalidProviderError(f"{name} must be a datetime or null")
