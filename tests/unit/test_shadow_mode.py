"""RED tests for M6.7 — Shadow mode with configurable opportunity count, elapsed time and data-quality conditions.

Tests define:
- ShadowModeEvaluator: evaluates strategy eligibility for shadow/paper trading
- ShadowConfig: configurable opportunity count, elapsed time, data-quality conditions
- ShadowResult: pass/fail verdict with reasons
- Opportunity count check: minimum number of trading opportunities required
- Elapsed time check: minimum observation period elapsed
- Data quality check: minimum data completeness / quality thresholds
- All conditions must pass for shadow mode to be eligible
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.shadow_mode import (
    ShadowConfig,
    ShadowModeEvaluator,
    ShadowResult,
    shadow_mode_eligible,
)


def test_shadow_config_creates():
    """ShadowConfig can be created with default values."""
    config = ShadowConfig()
    assert config.min_opportunities == 10
    assert config.min_elapsed_minutes == 60
    assert config.min_data_quality_pct == Decimal(90)


def test_shadow_config_custom_values():
    """ShadowConfig accepts custom values."""
    config = ShadowConfig(
        min_opportunities=20,
        min_elapsed_minutes=120,
        min_data_quality_pct=Decimal(95),
    )
    assert config.min_opportunities == 20
    assert config.min_elapsed_minutes == 120
    assert config.min_data_quality_pct == Decimal(95)


def test_shadow_result_creates():
    """ShadowResult can be created."""
    result = ShadowResult(
        eligible=True,
        opportunity_count=15,
        elapsed_minutes=90,
        data_quality_pct=Decimal(95),
        reasons=[],
    )
    assert result.eligible is True


def test_shadow_mode_eligible_all_pass():
    """shadow_mode_eligible returns True when all conditions pass."""
    result = shadow_mode_eligible(
        opportunity_count=15,
        elapsed_minutes=90,
        data_quality_pct=Decimal(95),
        config=ShadowConfig(
            min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
        ),
    )
    assert result.eligible is True
    assert result.reasons == []


def test_shadow_mode_not_eligible_too_few_opportunities():
    """shadow_mode_eligible returns False when opportunity count is too low."""
    result = shadow_mode_eligible(
        opportunity_count=5,
        elapsed_minutes=90,
        data_quality_pct=Decimal(95),
        config=ShadowConfig(
            min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
        ),
    )
    assert result.eligible is False
    assert "opportunity" in " ".join(result.reasons).lower()


def test_shadow_mode_not_eligible_insufficient_elapsed_time():
    """shadow_mode_eligible returns False when elapsed time is insufficient."""
    result = shadow_mode_eligible(
        opportunity_count=15,
        elapsed_minutes=30,
        data_quality_pct=Decimal(95),
        config=ShadowConfig(
            min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
        ),
    )
    assert result.eligible is False
    assert "elapsed" in " ".join(result.reasons).lower()


def test_shadow_mode_not_eligible_poor_data_quality():
    """shadow_mode_eligible returns False when data quality is poor."""
    result = shadow_mode_eligible(
        opportunity_count=15,
        elapsed_minutes=90,
        data_quality_pct=Decimal(80),
        config=ShadowConfig(
            min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
        ),
    )
    assert result.eligible is False
    assert "data" in " ".join(result.reasons).lower()


def test_shadow_mode_not_eligible_multiple_failures():
    """shadow_mode_eligible returns False with multiple failing conditions."""
    result = shadow_mode_eligible(
        opportunity_count=3,
        elapsed_minutes=10,
        data_quality_pct=Decimal(50),
        config=ShadowConfig(
            min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
        ),
    )
    assert result.eligible is False
    assert len(result.reasons) == 3


def test_shadow_mode_evaluator_creates():
    """ShadowModeEvaluator can be created."""
    evaluator = ShadowModeEvaluator()
    assert evaluator is not None


def test_shadow_mode_evaluator_evaluate():
    """ShadowModeEvaluator.evaluate returns ShadowResult."""
    evaluator = ShadowModeEvaluator()
    config = ShadowConfig(
        min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
    )
    result = evaluator.evaluate(
        opportunity_count=15,
        elapsed_minutes=90,
        data_quality_pct=Decimal(95),
        config=config,
    )
    assert isinstance(result, ShadowResult)
    assert result.eligible is True


def test_shadow_mode_deterministic():
    """Same inputs yield identical shadow mode results."""
    config = ShadowConfig(
        min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
    )
    r1 = shadow_mode_eligible(15, 90, Decimal(95), config)
    r2 = shadow_mode_eligible(15, 90, Decimal(95), config)
    assert r1.eligible == r2.eligible
    assert r1.reasons == r2.reasons


def test_shadow_mode_boundary_opportunity_count():
    """Opportunity count exactly at minimum passes."""
    config = ShadowConfig(
        min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
    )
    result = shadow_mode_eligible(10, 60, Decimal(90), config)
    assert result.eligible is True


def test_shadow_mode_boundary_below_opportunity_count():
    """Opportunity count one below minimum fails."""
    config = ShadowConfig(
        min_opportunities=10, min_elapsed_minutes=60, min_data_quality_pct=Decimal(90)
    )
    result = shadow_mode_eligible(9, 60, Decimal(90), config)
    assert result.eligible is False
