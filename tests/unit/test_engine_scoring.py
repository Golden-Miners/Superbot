"""RED tests for M3.7 — Engine scoring with weighted dimensions.

Covers:
- Individual dimension scoring (safety/correctness, compatibility,
  reproducibility, resource efficiency, maintainability, performance)
- Weighted total calculation
- Hard disqualifier checking
- Qualification logic (>=80/100, mandatory gates, no unresolved risk)
- score_engine end-to-end
- compare_engines best-qualified selection
- Score clamping (0-100)
- Edge cases (None values, zero values, all-pass/fail)

Stdlib-only. No import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from superbot.engine.engine_scoring import (
    QUALIFYING_SCORE,
    WEIGHT_COMPATIBILITY,
    WEIGHT_MAINTAINABILITY,
    WEIGHT_PERFORMANCE,
    WEIGHT_REPRODUCIBILITY,
    WEIGHT_RESOURCE_EFFICIENCY,
    WEIGHT_SAFETY_CORRECTNESS,
    Disqualifier,
    EngineScore,
    EngineScoreResult,
    check_disqualifiers,
    clamp_score,
    compare_engines,
    score_compatibility,
    score_engine,
    score_maintainability,
    score_performance,
    score_reproducibility,
    score_resource_efficiency,
    score_safety_correctness,
)

# --- Weight constants ---


def test_weights_sum_to_100():
    """All weights sum to 100."""
    total = (
        WEIGHT_SAFETY_CORRECTNESS
        + WEIGHT_COMPATIBILITY
        + WEIGHT_REPRODUCIBILITY
        + WEIGHT_RESOURCE_EFFICIENCY
        + WEIGHT_MAINTAINABILITY
        + WEIGHT_PERFORMANCE
    )
    assert total == 100


def test_qualifying_score_is_80():
    """Qualifying score threshold is 80."""
    assert QUALIFYING_SCORE == 80


# --- clamp_score ---


def test_clamp_score_below_zero():
    """Clamp below zero returns 0."""
    assert clamp_score(-5.0) == 0.0


def test_clamp_score_above_100():
    """Clamp above 100 returns 100."""
    assert clamp_score(105.0) == 100.0


def test_clamp_score_in_range():
    """Clamp in range returns same value."""
    assert clamp_score(50.0) == 50.0


def test_clamp_score_boundaries():
    """Clamp at exact boundaries returns same value."""
    assert clamp_score(0.0) == 0.0
    assert clamp_score(100.0) == 100.0


# --- score_safety_correctness ---


def test_safety_correctness_all_pass():
    """Safety/correctness score is 100 when all criteria pass."""
    assert score_safety_correctness(True, True, True) == 100.0


def test_safety_correctness_failed():
    """Safety/correctness score is 0 when correctness failed."""
    assert score_safety_correctness(False, True, True) == 0.0


def test_safety_correctness_not_all_repetitions():
    """Safety/correctness score is 20 when not all repetitions pass."""
    assert score_safety_correctness(True, False, True) == 20.0


def test_safety_correctness_no_deterministic_risk():
    """Safety/correctness score is 40 when deterministic risk not enforced."""
    assert score_safety_correctness(True, True, False) == 40.0


# --- score_compatibility ---


def test_compatibility_all_true():
    """Compatibility score is 100 when all criteria true."""
    assert score_compatibility(True, True, True) == 100.0


def test_compatibility_all_false():
    """Compatibility score is 0 when all criteria false."""
    assert score_compatibility(False, False, False) == 0.0


def test_compatibility_partial():
    """Compatibility score is sum of individual criteria."""
    assert score_compatibility(True, False, False) == 40.0
    assert score_compatibility(False, True, False) == 30.0
    assert score_compatibility(False, False, True) == 30.0


# --- score_reproducibility ---


def test_reproducibility_all_true():
    """Reproducibility score is 100 when all criteria true."""
    assert score_reproducibility(True, True, True) == 100.0


def test_reproducibility_all_false():
    """Reproducibility score is 0 when all criteria false."""
    assert score_reproducibility(False, False, False) == 0.0


# --- score_resource_efficiency ---


def test_resource_efficiency_all_within_thresholds():
    """Resource efficiency score is 100 when all within thresholds."""
    assert score_resource_efficiency(100.0, 50.0, 100.0) == 100.0


def test_resource_efficiency_all_exceed():
    """Resource efficiency score is reduced when all exceed thresholds."""
    result = score_resource_efficiency(600.0, 200.0, 2000.0)
    assert result < 100.0
    assert result == 0.0  # all three exceed -> 100 - 33 - 33 - 34 = 0


def test_resource_efficiency_none_values():
    """Resource efficiency handles None values (no penalty)."""
    assert score_resource_efficiency(None, None, None) == 100.0


def test_resource_efficiency_custom_thresholds():
    """Resource efficiency uses custom thresholds."""
    # Peak RSS 300MB with default threshold 500MB - no penalty
    assert score_resource_efficiency(300.0, None, None) == 100.0
    # Peak RSS 300MB with custom threshold 200MB - penalty
    result = score_resource_efficiency(
        300.0, None, None, thresholds={"max_peak_rss_mb": 200.0}
    )
    assert result < 100.0


# --- score_maintainability ---


def test_maintainability_all_true():
    """Maintainability score is 100 when all criteria true."""
    assert score_maintainability(True, True, True) == 100.0


def test_maintainability_all_false():
    """Maintainability score is 0 when all criteria false."""
    assert score_maintainability(False, False, False) == 0.0


# --- score_performance ---


def test_performance_all_within_thresholds():
    """Performance score is 100 when all within thresholds."""
    assert score_performance(200.0, 1000.0, 0.001) == 100.0


def test_performance_all_exceed():
    """Performance score is reduced when all exceed thresholds."""
    result = score_performance(50.0, 10000.0, 0.5)
    assert result == 0.0


def test_performance_none_values():
    """Performance handles None values (no penalty)."""
    assert score_performance(None, None, None) == 100.0


# --- EngineScore.weighted_total ---


def test_weighted_total_all_100():
    """Weighted total is 100 when all dimensions are 100."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    assert score.weighted_total() == 100.0


def test_weighted_total_all_0():
    """Weighted total is 0 when all dimensions are 0."""
    score = EngineScore(
        engine="test",
        safety_correctness=0.0,
        compatibility=0.0,
        reproducibility=0.0,
        resource_efficiency=0.0,
        maintainability=0.0,
        performance=0.0,
    )
    assert score.weighted_total() == 0.0


def test_weighted_total_partial():
    """Weighted total calculation with partial scores."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,  # 30
        compatibility=100.0,  # 20
        reproducibility=0.0,  # 0
        resource_efficiency=0.0,  # 0
        maintainability=0.0,  # 0
        performance=0.0,  # 0
    )
    assert score.weighted_total() == 50.0


# --- check_disqualifiers ---


def test_disqualifiers_none_when_all_pass():
    """No disqualifiers when all criteria pass."""
    disqualifiers, mandatory_passed = check_disqualifiers(
        correctness_passed=True,
        deterministic_risk_enforced=True,
        critical_security_issue=False,
        unacceptable_license=False,
        unresolved_critical_integration_risk=False,
    )
    assert len(disqualifiers) == 0
    assert mandatory_passed is True


def test_disqualifiers_correctness_failure():
    """Correctness failure is a hard disqualifier."""
    disqualifiers, mandatory_passed = check_disqualifiers(
        correctness_passed=False,
        deterministic_risk_enforced=True,
        critical_security_issue=False,
        unacceptable_license=False,
        unresolved_critical_integration_risk=False,
    )
    assert len(disqualifiers) == 1
    assert disqualifiers[0].name == "mandatory_correctness_failure"
    assert mandatory_passed is False


def test_disqualifiers_no_deterministic_risk():
    """Missing deterministic risk is a hard disqualifier."""
    disqualifiers, mandatory_passed = check_disqualifiers(
        correctness_passed=True,
        deterministic_risk_enforced=False,
        critical_security_issue=False,
        unacceptable_license=False,
        unresolved_critical_integration_risk=False,
    )
    assert len(disqualifiers) == 1
    assert disqualifiers[0].name == "cannot_enforce_deterministic_risk"
    assert mandatory_passed is False


def test_disqualifiers_security_issue():
    """Critical security issue is a hard disqualifier."""
    disqualifiers, _ = check_disqualifiers(
        correctness_passed=True,
        deterministic_risk_enforced=True,
        critical_security_issue=True,
        unacceptable_license=False,
        unresolved_critical_integration_risk=False,
    )
    assert len(disqualifiers) == 1
    assert disqualifiers[0].name == "unresolved_critical_security_issue"


def test_disqualifiers_unacceptable_license():
    """Unacceptable license is a hard disqualifier."""
    disqualifiers, _ = check_disqualifiers(
        correctness_passed=True,
        deterministic_risk_enforced=True,
        critical_security_issue=False,
        unacceptable_license=True,
        unresolved_critical_integration_risk=False,
    )
    assert len(disqualifiers) == 1
    assert disqualifiers[0].name == "unacceptable_terms_license"


def test_disqualifiers_multiple():
    """Multiple disqualifiers are all reported."""
    disqualifiers, mandatory_passed = check_disqualifiers(
        correctness_passed=False,
        deterministic_risk_enforced=False,
        critical_security_issue=True,
        unacceptable_license=True,
        unresolved_critical_integration_risk=True,
    )
    assert len(disqualifiers) == 4
    assert mandatory_passed is False


# --- EngineScoreResult properties ---


def test_score_result_is_qualified_all_pass():
    """Engine is qualified when all criteria pass and score >= 80."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(),
        mandatory_gates_passed=True,
        unresolved_critical_integration_risk=False,
    )
    assert result.is_disqualified is False
    assert result.is_qualified is True
    assert result.total_score == 100.0


def test_score_result_disqualified():
    """Engine is not qualified when disqualified."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    dq = Disqualifier(
        name="test_dq",
        reason="test reason",
        evidence_ref="test evidence",
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(dq,),
        mandatory_gates_passed=True,
        unresolved_critical_integration_risk=False,
    )
    assert result.is_disqualified is True
    assert result.is_qualified is False


def test_score_result_mandatory_gates_not_passed():
    """Engine is not qualified when mandatory gates not all passed."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(),
        mandatory_gates_passed=False,
        unresolved_critical_integration_risk=False,
    )
    assert result.is_qualified is False


def test_score_result_unresolved_risk():
    """Engine is not qualified when unresolved critical integration risk."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(),
        mandatory_gates_passed=True,
        unresolved_critical_integration_risk=True,
    )
    assert result.is_qualified is False


def test_score_result_score_below_threshold():
    """Engine is not qualified when score < 80."""
    score = EngineScore(
        engine="test",
        safety_correctness=50.0,
        compatibility=50.0,
        reproducibility=50.0,
        resource_efficiency=50.0,
        maintainability=50.0,
        performance=50.0,
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(),
        mandatory_gates_passed=True,
        unresolved_critical_integration_risk=False,
    )
    assert result.total_score == 50.0
    assert result.is_qualified is False


def test_score_result_qualification_reason():
    """Qualification reason reflects status."""
    score = EngineScore(
        engine="test",
        safety_correctness=100.0,
        compatibility=100.0,
        reproducibility=100.0,
        resource_efficiency=100.0,
        maintainability=100.0,
        performance=100.0,
    )
    result = EngineScoreResult(
        engine="test",
        score=score,
        disqualifiers=(),
        mandatory_gates_passed=True,
        unresolved_critical_integration_risk=False,
    )
    assert "qualified" in result.qualification_reason
    assert "100.0" in result.qualification_reason


# --- score_engine ---


def test_score_engine_fully_qualified():
    """score_engine produces qualified result for perfect engine."""
    result = score_engine(
        engine="custom_baseline",
        correctness_passed=True,
        correctness_gate_passed_on_all_repetitions=True,
        deterministic_replay_passed=True,
        noise_rule_defined=True,
        seed_fixed_datasets=True,
        deterministic_risk_enforced=True,
        standard_contracts_used=True,
        split_chronological_used=True,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
        peak_rss_mb=100.0,
        disk_io_mb=50.0,
        startup_ms=100.0,
        median_throughput_trades_per_sec=200.0,
        median_latency_ms=1000.0,
        failure_rate=0.001,
    )
    assert result.is_qualified is True
    assert result.total_score == 100.0
    assert len(result.disqualifiers) == 0
    assert result.mandatory_gates_passed is True
    assert result.unresolved_critical_integration_risk is False


def test_score_engine_disqualified_correctness_failure():
    """score_engine disqualifies engine with correctness failure."""
    result = score_engine(
        engine="failing_engine",
        correctness_passed=False,
        deterministic_risk_enforced=True,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
    )
    assert result.is_qualified is False
    assert result.is_disqualified is True
    assert result.mandatory_gates_passed is False
    assert any(d.name == "mandatory_correctness_failure" for d in result.disqualifiers)


def test_score_engine_disqualified_no_deterministic_risk():
    """score_engine disqualifies engine without deterministic risk."""
    result = score_engine(
        engine="risky_engine",
        correctness_passed=True,
        deterministic_risk_enforced=False,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
    )
    assert result.is_qualified is False
    assert result.is_disqualified is True
    assert any(d.name == "cannot_enforce_deterministic_risk" for d in result.disqualifiers)


def test_score_engine_disqualified_security_issue():
    """score_engine disqualifies engine with critical security issue."""
    result = score_engine(
        engine="insecure_engine",
        correctness_passed=True,
        deterministic_risk_enforced=True,
        critical_security_issue=True,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
    )
    assert result.is_qualified is False
    assert result.is_disqualified is True
    assert any(d.name == "unresolved_critical_security_issue" for d in result.disqualifiers)


def test_score_engine_disqualified_unacceptable_license():
    """score_engine disqualifies engine with unacceptable license."""
    result = score_engine(
        engine="bad_license_engine",
        correctness_passed=True,
        deterministic_risk_enforced=True,
        unacceptable_license=True,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
    )
    assert result.is_qualified is False
    assert result.is_disqualified is True
    assert any(d.name == "unacceptable_terms_license" for d in result.disqualifiers)


def test_score_engine_unresolved_integration_risk():
    """score_engine marks not qualified when unresolved integration risk."""
    result = score_engine(
        engine="risky_integration_engine",
        correctness_passed=True,
        deterministic_risk_enforced=True,
        unresolved_critical_integration_risk=True,
        stdlib_only=True,
        versioned_configs=True,
        no_ten_llm_agents=True,
    )
    assert result.is_qualified is False
    assert result.unresolved_critical_integration_risk is True


def test_score_engine_score_below_threshold():
    """score_engine marks not qualified when score below 80."""
    result = score_engine(
        engine="low_score_engine",
        correctness_passed=True,
        correctness_gate_passed_on_all_repetitions=True,
        deterministic_risk_enforced=True,
        deterministic_replay_passed=False,
        noise_rule_defined=False,
        seed_fixed_datasets=False,
        stdlib_only=False,
        versioned_configs=False,
        no_ten_llm_agents=False,
    )
    assert result.total_score < QUALIFYING_SCORE
    assert result.is_qualified is False


# --- compare_engines ---


def test_compare_engines_returns_best_qualified():
    """compare_engines returns the qualified engine with highest score."""
    results = [
        score_engine(
            engine="engine_a",
            correctness_passed=True,
            correctness_gate_passed_on_all_repetitions=True,
            deterministic_replay_passed=True,
            noise_rule_defined=True,
            seed_fixed_datasets=True,
            deterministic_risk_enforced=True,
            standard_contracts_used=True,
            split_chronological_used=True,
            stdlib_only=True,
            versioned_configs=True,
            no_ten_llm_agents=True,
            peak_rss_mb=100.0,
            disk_io_mb=50.0,
            startup_ms=100.0,
            median_throughput_trades_per_sec=200.0,
            median_latency_ms=1000.0,
            failure_rate=0.001,
        ),
        score_engine(
            engine="engine_b",
            correctness_passed=True,
            correctness_gate_passed_on_all_repetitions=True,
            deterministic_replay_passed=False,
            noise_rule_defined=True,
            seed_fixed_datasets=True,
            deterministic_risk_enforced=True,
            standard_contracts_used=True,
            split_chronological_used=True,
            stdlib_only=True,
            versioned_configs=True,
            no_ten_llm_agents=True,
            peak_rss_mb=100.0,
            disk_io_mb=50.0,
            startup_ms=100.0,
            median_throughput_trades_per_sec=200.0,
            median_latency_ms=1000.0,
            failure_rate=0.001,
        ),
    ]
    best = compare_engines(results)
    assert best is not None
    assert best.engine == "engine_a"
    assert best.total_score > results[1].total_score


def test_compare_engines_none_when_none_qualified():
    """compare_engines returns None when no engine qualifies."""
    results = [
        score_engine(
            engine="disqualified_engine",
            correctness_passed=False,
            deterministic_risk_enforced=True,
            stdlib_only=True,
            versioned_configs=True,
            no_ten_llm_agents=True,
        ),
    ]
    assert compare_engines(results) is None


def test_compare_engines_empty_list():
    """compare_engines returns None for empty list."""
    assert compare_engines([]) is None