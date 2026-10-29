"""RED tests for M3.4 — QuantConnect LEAN engine POC adapter.

Tests define:
- LEAN adapter raises LeanNotInstalled when package absent
- Adapter runs equivalence acceptance using M3.2 canonical fixture/costs
- Correctness gate passes for LEAN (matches custom baseline semantics)
- Same fixtures/rules/costs/splits as M3.2 equivalence framework
- Adapter under test requires quantconnect-lean installed in isolated env
"""

from __future__ import annotations

import importlib.util

import pytest

from superbot.engine.equivalence import CostConvention, EquivalenceFixture
from superbot.engine.quantconnect_adapter import (
    LeanAdapter,
    LeanNotInstalled,
)

LEAN_AVAILABLE = importlib.util.find_spec("quantconnect") is not None


def test_lean_not_installed_raises():
    """Adapter raises LeanNotInstalled when quantconnect-lean is not installed."""
    with pytest.raises(LeanNotInstalled):
        LeanAdapter()


@pytest.mark.skipif(not LEAN_AVAILABLE, reason="quantconnect-lean not installed")
def test_lean_adapter_instantiates():
    """Adapter instantiates when quantconnect-lean is available."""
    adapter = LeanAdapter()
    assert adapter is not None


@pytest.mark.skipif(not LEAN_AVAILABLE, reason="quantconnect-lean not installed")
def test_lean_runs_equivalence_and_passes_correctness_gate():
    """Adapter runs equivalence on LEAN and passes correctness gate."""
    adapter = LeanAdapter()
    fx = EquivalenceFixture.canonical()
    cc = CostConvention.default()
    result = adapter.run_equivalence(fx, cc)
    assert result.engine == "lean"
    assert result.fixture == "canonical_10bar"
    assert result.correctness_gate_passed is True
    assert result.event_count > 0
