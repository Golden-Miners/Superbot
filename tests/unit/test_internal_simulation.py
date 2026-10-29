"""RED tests for M6.8 — Internal-simulation eligibility and three-failed-validation-attempt version archive rule.

Tests define:
- InternalSimulationEvaluator: determines if a strategy version is eligible for internal simulation
- InternalSimulationConfig: configurable eligibility criteria
- InternalSimulationResult: pass/fail verdict with reasons
- VersionArchiveRule: tracks validation attempts and archives after 3 failures
- Internal simulation requires passing cost-adjusted gates and robustness checks
- Three-failed-validation-attempt rule: version archived after 3 consecutive failed validations
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.strategy.internal_simulation import (
    InternalSimulationConfig,
    InternalSimulationResult,
    VersionArchiveRule,
    evaluate_internal_simulation_eligibility,
    is_version_archived,
    record_validation_attempt,
)


def test_internal_simulation_config_creates():
    """InternalSimulationConfig can be created with defaults."""
    config = InternalSimulationConfig()
    assert config.min_cost_adjusted_return_pct == Decimal(5)
    assert config.min_sharpe == Decimal("1.0")
    assert config.max_max_dd_pct == Decimal(15)
    assert config.max_validation_failures == 3


def test_internal_simulation_config_custom():
    """InternalSimulationConfig accepts custom values."""
    config = InternalSimulationConfig(
        min_cost_adjusted_return_pct=Decimal(8),
        min_sharpe=Decimal("1.5"),
        max_max_dd_pct=Decimal(10),
        max_validation_failures=5,
    )
    assert config.min_cost_adjusted_return_pct == Decimal(8)
    assert config.min_sharpe == Decimal("1.5")
    assert config.max_max_dd_pct == Decimal(10)
    assert config.max_validation_failures == 5


def test_internal_simulation_result_creates():
    """InternalSimulationResult can be created."""
    result = InternalSimulationResult(
        eligible=True,
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(8),
        reasons=[],
    )
    assert result.eligible is True


def test_evaluate_internal_simulation_eligible_all_pass():
    """evaluate_internal_simulation_eligibility returns True when all criteria pass."""
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(8),
        config=InternalSimulationConfig(
            min_cost_adjusted_return_pct=Decimal(5),
            min_sharpe=Decimal("1.0"),
            max_max_dd_pct=Decimal(15),
        ),
    )
    assert result.eligible is True
    assert result.reasons == []


def test_evaluate_internal_simulation_not_eligible_low_return():
    """evaluate_internal_simulation_eligibility returns False when cost-adjusted return too low."""
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(2),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(8),
        config=InternalSimulationConfig(
            min_cost_adjusted_return_pct=Decimal(5),
            min_sharpe=Decimal("1.0"),
            max_max_dd_pct=Decimal(15),
        ),
    )
    assert result.eligible is False
    assert "return" in " ".join(result.reasons).lower()


def test_evaluate_internal_simulation_not_eligible_low_sharpe():
    """evaluate_internal_simulation_eligibility returns False when Sharpe too low."""
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("0.5"),
        max_dd_pct=Decimal(8),
        config=InternalSimulationConfig(
            min_cost_adjusted_return_pct=Decimal(5),
            min_sharpe=Decimal("1.0"),
            max_max_dd_pct=Decimal(15),
        ),
    )
    assert result.eligible is False
    assert "sharpe" in " ".join(result.reasons).lower()


def test_evaluate_internal_simulation_not_eligible_high_dd():
    """evaluate_internal_simulation_eligibility returns False when max DD too high."""
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(25),
        config=InternalSimulationConfig(
            min_cost_adjusted_return_pct=Decimal(5),
            min_sharpe=Decimal("1.0"),
            max_max_dd_pct=Decimal(15),
        ),
    )
    assert result.eligible is False
    assert (
        "drawdown" in " ".join(result.reasons).lower() or "dd" in " ".join(result.reasons).lower()
    )


def test_evaluate_internal_simulation_not_eligible_multiple_failures():
    """evaluate_internal_simulation_eligibility returns False with multiple failing criteria."""
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(2),
        sharpe=Decimal("0.5"),
        max_dd_pct=Decimal(25),
        config=InternalSimulationConfig(
            min_cost_adjusted_return_pct=Decimal(5),
            min_sharpe=Decimal("1.0"),
            max_max_dd_pct=Decimal(15),
        ),
    )
    assert result.eligible is False
    assert len(result.reasons) == 3


def test_internal_simulation_deterministic():
    """Same inputs yield identical internal simulation results."""
    config = InternalSimulationConfig(
        min_cost_adjusted_return_pct=Decimal(5),
        min_sharpe=Decimal("1.0"),
        max_max_dd_pct=Decimal(15),
    )
    r1 = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(8),
        config=config,
    )
    r2 = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(10),
        sharpe=Decimal("1.5"),
        max_dd_pct=Decimal(8),
        config=config,
    )
    assert r1.eligible == r2.eligible
    assert r1.reasons == r2.reasons


def test_internal_simulation_boundary_at_threshold():
    """Values exactly at threshold pass."""
    config = InternalSimulationConfig(
        min_cost_adjusted_return_pct=Decimal(5),
        min_sharpe=Decimal("1.0"),
        max_max_dd_pct=Decimal(15),
    )
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal(5),
        sharpe=Decimal("1.0"),
        max_dd_pct=Decimal(15),
        config=config,
    )
    assert result.eligible is True


def test_internal_simulation_boundary_below_threshold():
    """Values just below threshold fail."""
    config = InternalSimulationConfig(
        min_cost_adjusted_return_pct=Decimal(5),
        min_sharpe=Decimal("1.0"),
        max_max_dd_pct=Decimal(15),
    )
    result = evaluate_internal_simulation_eligibility(
        cost_adjusted_return_pct=Decimal("4.99"),
        sharpe=Decimal("0.99"),
        max_dd_pct=Decimal("15.01"),
        config=config,
    )
    assert result.eligible is False
    assert len(result.reasons) == 3


def test_version_archive_rule_creates():
    """VersionArchiveRule can be created."""
    rule = VersionArchiveRule()
    assert rule is not None


def test_version_archive_rule_records_attempts():
    """VersionArchiveRule tracks validation attempts per version."""
    rule = VersionArchiveRule(max_failures=3)
    assert not rule.is_archived("v1")
    record_validation_attempt(rule, "v1", passed=False)
    assert not rule.is_archived("v1")
    record_validation_attempt(rule, "v1", passed=False)
    assert not rule.is_archived("v1")
    record_validation_attempt(rule, "v1", passed=False)
    assert rule.is_archived("v1")


def test_version_archive_rule_passing_resets_failures():
    """A passing validation resets the failure count for a version."""
    rule = VersionArchiveRule(max_failures=3)
    record_validation_attempt(rule, "v1", passed=False)
    record_validation_attempt(rule, "v1", passed=False)
    record_validation_attempt(rule, "v1", passed=True)
    record_validation_attempt(rule, "v1", passed=False)
    assert not rule.is_archived("v1")


def test_version_archive_rule_three_failures_archives():
    """Three failed validation attempts archive the version."""
    rule = VersionArchiveRule(max_failures=3)
    for _ in range(3):
        record_validation_attempt(rule, "v1", passed=False)
    assert rule.is_archived("v1")


def test_version_archive_rule_not_archived_before_three_failures():
    """Version not archived before three failures."""
    rule = VersionArchiveRule(max_failures=3)
    record_validation_attempt(rule, "v1", passed=False)
    record_validation_attempt(rule, "v1", passed=False)
    assert not rule.is_archived("v1")


def test_record_validation_attempt_function():
    """record_validation_attempt records a validation attempt."""
    rule = VersionArchiveRule()
    record_validation_attempt(rule, "v1", passed=True)
    assert not rule.is_archived("v1")


def test_is_version_archived_function():
    """is_version_archived checks archive status."""
    rule = VersionArchiveRule()
    assert not is_version_archived(rule, "v1")
    record_validation_attempt(rule, "v1", passed=False)
    record_validation_attempt(rule, "v1", passed=False)
    record_validation_attempt(rule, "v1", passed=False)
    assert is_version_archived(rule, "v1")
