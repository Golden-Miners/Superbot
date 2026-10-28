"""Tests for the provider/source metadata contract (M2.1).

Represents a market-data provider (e.g. XM MT5) with its own identity,
discovery/provenance metadata and verification status. Unknown or missing
metadata is preserved explicitly; broker-typical values are never substituted.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from superbot.contracts.provider import (
    InvalidProviderError,
    ProviderSpec,
    ProviderType,
    ProviderVerificationStatus,
)


def test_valid_provider_spec_accepted():
    spec = ProviderSpec(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        provider_name="XM MetaTrader 5",
        provider_type=ProviderType.MT5,
        source_metadata_ref="mt5:terminal:XM",
        discovered_at_utc=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        verification_status=ProviderVerificationStatus.VERIFIED,
        verified_at_utc=datetime(2026, 10, 28, 12, 30, tzinfo=UTC),
        read_only=True,
    )
    assert spec.provider_id == "xm-mt5"
    assert spec.read_only is True


def test_unknown_metadata_preserved_not_guessed():
    spec = ProviderSpec(
        schema_version="1.0.0",
        provider_id="xm-mt5",
        provider_name=None,
        provider_type=ProviderType.UNKNOWN,
        source_metadata_ref=None,
        discovered_at_utc=None,
        verification_status=ProviderVerificationStatus.UNAVAILABLE,
        verified_at_utc=None,
        read_only=False,
    )
    assert spec.provider_name is None
    assert spec.provider_type == ProviderType.UNKNOWN
    assert spec.source_metadata_ref is None
    assert spec.discovered_at_utc is None
    assert spec.verification_status == ProviderVerificationStatus.UNAVAILABLE
    assert spec.verified_at_utc is None


def test_required_fields_rejected_when_missing():
    with pytest.raises(InvalidProviderError):
        ProviderSpec(
            schema_version="1.0.0",
            provider_id="",
            provider_name="XM",
            provider_type=ProviderType.MT5,
            source_metadata_ref="x",
        )


def test_invalid_provider_type_rejected():
    with pytest.raises(InvalidProviderError):
        ProviderSpec(
            schema_version="1.0.0",
            provider_id="xm-mt5",
            provider_name="XM",
            provider_type="not-a-type",  # type: ignore[arg-type]
            source_metadata_ref="x",
        )
