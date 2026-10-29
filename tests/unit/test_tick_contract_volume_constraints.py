"""RED tests for M4.5 — Verified tick/contract/volume constraints; block if missing/stale.

Tests define:
- Tick constraints validated before execution: non-zero tick size, valid tick value
- Contract constraints validated: valid contract symbol, non-null expiry, valid multiplier
- Volume constraints validated: positive volume, volume within min/max bounds
- Missing/stale contract data blocks execution with explicit error
- Missing/stale tick data blocks execution with explicit error
- Missing/stale volume data blocks execution with explicit error
- Constraint validation applied to both entry and exit fills
- Deterministic: same inputs yield identical constraint validation results
- Contract expiry staleness detected: past expiry blocks execution
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from superbot.simulation.next_bar_open import (
    ConstraintValidator,
    ContractConstraintError,
    InstrumentSpec,
    NextBarOpenSimulator,
    VolumeConstraintError,
)


def test_constraint_validator_defaults():
    """ConstraintValidator with valid config passes validation."""
    cv = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    assert cv.tick_size == Decimal("0.01")
    assert cv.tick_value == Decimal("1.00")
    assert cv.contract_symbol == "ESZ25"


def test_tick_size_zero_blocks():
    """Zero tick size blocks execution."""
    with pytest.raises(ContractConstraintError):
        ConstraintValidator(
            tick_size=Decimal(0),
            tick_value=Decimal("1.00"),
            contract_symbol="ESZ25",
            contract_expiry=date.today() + timedelta(days=30),
            contract_multiplier=Decimal(50),
        )


def test_tick_value_zero_blocks():
    """Zero tick value blocks execution."""
    with pytest.raises(ContractConstraintError):
        ConstraintValidator(
            tick_size=Decimal("0.01"),
            tick_value=Decimal(0),
            contract_symbol="ESZ25",
            contract_expiry=date.today() + timedelta(days=30),
            contract_multiplier=Decimal(50),
        )


def test_contract_symbol_missing_blocks():
    """Missing/empty contract symbol blocks execution."""
    with pytest.raises(ContractConstraintError):
        ConstraintValidator(
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1.00"),
            contract_symbol="",
            contract_expiry=date.today() + timedelta(days=30),
            contract_multiplier=Decimal(50),
        )


def test_contract_expiry_past_blocks():
    """Past contract expiry blocks execution (stale contract)."""
    with pytest.raises(ContractConstraintError):
        ConstraintValidator(
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1.00"),
            contract_symbol="ESZ25",
            contract_expiry=date.today() - timedelta(days=1),
            contract_multiplier=Decimal(50),
        )


def test_contract_multiplier_zero_blocks():
    """Zero contract multiplier blocks execution."""
    with pytest.raises(ContractConstraintError):
        ConstraintValidator(
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1.00"),
            contract_symbol="ESZ25",
            contract_expiry=date.today() + timedelta(days=30),
            contract_multiplier=Decimal(0),
        )


def test_volume_zero_blocks():
    """Zero volume blocks execution."""
    cv = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    with pytest.raises(VolumeConstraintError):
        cv.validate_volume(Decimal(0))


def test_volume_below_min_blocks():
    """Volume below min blocks execution."""
    cv = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(10),
        max_volume=Decimal(100000),
    )
    with pytest.raises(VolumeConstraintError):
        cv.validate_volume(Decimal(5))


def test_volume_above_max_blocks():
    """Volume above max blocks execution."""
    cv = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100),
    )
    with pytest.raises(VolumeConstraintError):
        cv.validate_volume(Decimal(200))


def test_volume_valid_passes():
    """Volume within bounds passes validation."""
    cv = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    assert cv.validate_volume(Decimal(50)) == Decimal(50)


def test_simulator_allows_without_constraints_set():
    """NextBarOpenSimulator allows entry when no constraints are set (backwards compatible)."""
    sim = NextBarOpenSimulator()
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.event_type == "entry"


def test_simulator_blocks_with_stale_contract():
    """NextBarOpenSimulator blocks when contract is stale (past expiry)."""
    sim = NextBarOpenSimulator()
    with pytest.raises(ContractConstraintError):
        sim.set_constraints(
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1.00"),
            contract_symbol="ESZ25",
            contract_expiry=date.today() - timedelta(days=1),
            contract_multiplier=Decimal(50),
        )


def test_simulator_blocks_with_invalid_volume():
    """NextBarOpenSimulator blocks entry when volume invalid."""
    sim = NextBarOpenSimulator()
    sim.set_constraints(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(10),
        max_volume=Decimal(100000),
    )
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    with pytest.raises(VolumeConstraintError):
        sim.enter_long(
            bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"), qty=Decimal(1)
        )


def test_simulator_allows_valid_constraints():
    """NextBarOpenSimulator allows entry when all constraints valid."""
    sim = NextBarOpenSimulator()
    sim.set_constraints(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    bars = [
        (1, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"), Decimal("100.0")),
        (2, Decimal("100.0"), Decimal("102.0"), Decimal("98.0"), Decimal("101.0")),
    ]
    fill = sim.enter_long(bars, signal_index=0, stop=Decimal("99.0"), target=Decimal("104.0"))
    assert fill.event_type == "entry"


def test_constraint_validation_deterministic():
    """Same inputs yield identical constraint validation results."""
    cv1 = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    cv2 = ConstraintValidator(
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1.00"),
        contract_symbol="ESZ25",
        contract_expiry=date.today() + timedelta(days=30),
        contract_multiplier=Decimal(50),
        min_volume=Decimal(1),
        max_volume=Decimal(100000),
    )
    assert cv1.validate_volume(Decimal(10)) == cv2.validate_volume(Decimal(10))


def test_instrument_spec_null_tick_blocks():
    """InstrumentSpec with null tick size blocks constraint validation."""
    with pytest.raises(ContractConstraintError):
        InstrumentSpec(
            symbol="ESZ25",
            tick_size=None,
            tick_value=None,
            contract_multiplier=None,
            expiry=None,
        )


def test_instrument_spec_valid():
    """InstrumentSpec with valid fields passes constraint validation."""
    spec = InstrumentSpec(
        symbol="ESZ25",
        tick_size=Decimal("0.01"),
        tick_value=Decimal("12.50"),
        contract_multiplier=Decimal(50),
        expiry=date.today() + timedelta(days=30),
    )
    assert spec.symbol == "ESZ25"
    assert spec.tick_size == Decimal("0.01")
