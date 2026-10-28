"""Tests for the Instrument specification contract (schema.md section 2).

Null means absent, not zero. Missing/stale fields needed for simulation or
sizing must block that operation; broker-typical values are never substituted.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.contracts.instrument import (
    AssetClass,
    InstrumentSpec,
    InvalidInstrumentError,
    VerificationStatus,
)


def test_valid_instrument_spec_accepted():
    spec = InstrumentSpec(
        schema_version="1.0.0",
        instrument_id="XAUUSD",
        provider_id="xm-mt5",
        provider_symbol="XAUUSD",
        asset_class=AssetClass.METAL,
        quote_currency="USD",
        base_currency="XAU",
        contract_size=Decimal(100),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal(500),
        volume_step=Decimal("0.01"),
        price_precision=2,
        volume_precision=2,
        trade_sessions_ref="xm-mt5-sessions",
        server_timezone="UTC",
        verification_status=VerificationStatus.VERIFIED,
        source_metadata_ref="mt5:symbol_info:XAUUSD",
    )
    assert spec.instrument_id == "XAUUSD"
    assert spec.verification_status == VerificationStatus.VERIFIED


def test_required_fields_rejected_when_missing():
    with pytest.raises(InvalidInstrumentError):
        InstrumentSpec(
            schema_version="1.0.0",
            instrument_id="",
            provider_id="xm-mt5",
            provider_symbol="",
            asset_class=AssetClass.METAL,
            verification_status=VerificationStatus.VERIFIED,
            source_metadata_ref="x",
        )


def test_null_fields_stay_null_not_zero():
    spec = InstrumentSpec(
        schema_version="1.0.0",
        instrument_id="XAUUSD",
        provider_id="xm-mt5",
        provider_symbol="XAUUSD",
        asset_class=AssetClass.METAL,
        contract_size=None,
        tick_size=None,
        volume_min=None,
        verification_status=VerificationStatus.UNAVAILABLE,
        source_metadata_ref="x",
    )
    assert spec.contract_size is None
    assert spec.tick_size is None
    assert spec.volume_min is None
    assert spec.verification_status == VerificationStatus.UNAVAILABLE


def test_invalid_verification_status_rejected():
    with pytest.raises(InvalidInstrumentError):
        InstrumentSpec(
            schema_version="1.0.0",
            instrument_id="XAUUSD",
            provider_id="xm-mt5",
            provider_symbol="XAUUSD",
            asset_class=AssetClass.METAL,
            verification_status="not-a-status",  # type: ignore[arg-type]
            source_metadata_ref="x",
        )
