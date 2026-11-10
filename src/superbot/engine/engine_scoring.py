"""Engine scoring for M3.7 — weighted evaluation of POC candidate engines.

Scores each engine across six dimensions with defined weights:
  safety/correctness  30%
  compatibility       20%
  reproducibility     15%
  resource efficiency 15%
  maintainability     10%
  performance         10%

Hard disqualifiers (any one blocks qualification regardless of score):
  - mandatory correctness failure
  - inability to enforce Superbot deterministic risk
  - unresolved critical security issue
  - unacceptable terms/licence

Qualification requires:
  - total score >= 80/100
  - all mandatory gates passed
  - no unresolved critical integration risk

Stdlib-only. No import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass

# Weighted scoring dimensions (must sum to 100)
WEIGHT_SAFETY_CORRECTNESS = 30
WEIGHT_COMPATIBILITY = 20
WEIGHT_REPRODUCIBILITY = 15
WEIGHT_RESOURCE_EFFICIENCY = 15
WEIGHT_MAINTAINABILITY = 10
WEIGHT_PERFORMANCE = 10

QUALIFYING_SCORE = 80


@dataclass(frozen=True)
class EngineScore:
    """Per-dimension score for a candidate engine (0-100 each)."""

    engine: str
    safety_correctness: float  # 0-100
    compatibility: float  # 0-100
    reproducibility: float  # 0-100
    resource_efficiency: float  # 0-100
    maintainability: float  # 0-100
    performance: float  # 0-100

    def weighted_total(self) -> float:
        """Return the weighted total score (0-100)."""
        return (
            self.safety_correctness * WEIGHT_SAFETY_CORRECTNESS / 100
            + self.compatibility * WEIGHT_COMPATIBILITY / 100
            + self.reproducibility * WEIGHT_REPRODUCIBILITY / 100
            + self.resource_efficiency * WEIGHT_RESOURCE_EFFICIENCY / 100
            + self.maintainability * WEIGHT_MAINTAINABILITY / 100
            + self.performance * WEIGHT_PERFORMANCE / 100
        )


@dataclass(frozen=True)
class Disqualifier:
    """A hard disqualifier with reason and evidence reference."""

    name: str
    reason: str
    evidence_ref: str


@dataclass(frozen=True)
class EngineScoreResult:
    """Complete scoring outcome for a candidate engine."""

    engine: str
    score: EngineScore
    disqualifiers: tuple[Disqualifier, ...]
    mandatory_gates_passed: bool
    unresolved_critical_integration_risk: bool

    @property
    def total_score(self) -> float:
        """Return weighted total score (0-100)."""
        return self.score.weighted_total()

    @property
    def is_disqualified(self) -> bool:
        """Return True if any hard disqualifier applies."""
        return len(self.disqualifiers) > 0

    @property
    def is_qualified(self) -> bool:
        """Return True if engine qualifies for selection."""
        return (
            not self.is_disqualified
            and self.mandatory_gates_passed
            and not self.unresolved_critical_integration_risk
            and self.total_score >= QUALIFYING_SCORE
        )

    @property
    def qualification_reason(self) -> str:
        """Return human-readable qualification status."""
        if self.is_disqualified:
            names = ", ".join(d.name for d in self.disqualifiers)
            return f"disqualified: {names}"
        if not self.mandatory_gates_passed:
            return "not qualified: mandatory gates not all passed"
        if self.unresolved_critical_integration_risk:
            return "not qualified: unresolved critical integration risk"
        if self.total_score < QUALIFYING_SCORE:
            return f"not qualified: score {self.total_score:.1f} < {QUALIFYING_SCORE}"
        return f"qualified: score {self.total_score:.1f} >= {QUALIFYING_SCORE}"


def clamp_score(value: float) -> float:
    """Clamp a score to the 0-100 range."""
    return max(0.0, min(100.0, value))


def score_safety_correctness(
    correctness_passed: bool,
    correctness_gate_passed_on_all_repetitions: bool,
    deterministic_risk_enforced: bool,
) -> float:
    """Score safety/correctness dimension (0-100, weight 30%).

    Mandatory gate: correctness_passed must be True.
    """
    if not correctness_passed:
        return 0.0
    if not correctness_gate_passed_on_all_repetitions:
        return 20.0  # partial credit: correctness passed but not consistently
    if not deterministic_risk_enforced:
        return 40.0  # correctness works but deterministic risk not enforced
    return 100.0


def score_compatibility(
    deterministic_risk_enforced: bool,
    standard_contracts_used: bool,
    split_chronological_used: bool,
) -> float:
    """Score compatibility dimension (0-100, weight 20%).

    Compatibility with Superbot architecture: deterministic risk,
    canonical contracts, chronological splits.
    """
    score = 0.0
    if deterministic_risk_enforced:
        score += 40.0
    if standard_contracts_used:
        score += 30.0
    if split_chronological_used:
        score += 30.0
    return clamp_score(score)


def score_reproducibility(
    deterministic_replay_passed: bool,
    noise_rule_defined: bool,
    seed_fixed_datasets: bool,
) -> float:
    """Score reproducibility dimension (0-100, weight 15%).

    Reproducibility: deterministic replay, noise rule, fixed seed datasets.
    """
    score = 0.0
    if deterministic_replay_passed:
        score += 40.0
    if noise_rule_defined:
        score += 30.0
    if seed_fixed_datasets:
        score += 30.0
    return clamp_score(score)


def score_resource_efficiency(
    peak_rss_mb: float | None,
    disk_io_mb: float | None,
    startup_ms: float | None,
    thresholds: dict[str, float] | None = None,
) -> float:
    """Score resource efficiency dimension (0-100, weight 15%).

    thresholds: optional dict with keys 'max_peak_rss_mb', 'max_disk_io_mb',
    'max_startup_ms'. Defaults: RSS 500MB, disk IO 100MB, startup 1000ms.
    """
    thresholds = thresholds or {
        "max_peak_rss_mb": 500.0,
        "max_disk_io_mb": 100.0,
        "max_startup_ms": 1000.0,
    }

    score = 100.0
    if peak_rss_mb is not None and peak_rss_mb > thresholds["max_peak_rss_mb"]:
        score -= 33.0
    if disk_io_mb is not None and disk_io_mb > thresholds["max_disk_io_mb"]:
        score -= 33.0
    if startup_ms is not None and startup_ms > thresholds["max_startup_ms"]:
        score -= 34.0
    return clamp_score(score)


def score_maintainability(
    stdlib_only: bool,
    versioned_configs: bool,
    no_ten_llm_agents: bool,
) -> float:
    """Score maintainability dimension (0-100, weight 10%).

    Maintainability: stdlib-only code, versioned configs, shared framework
    (no ten separate LLM strategy agents).
    """
    score = 0.0
    if stdlib_only:
        score += 40.0
    if versioned_configs:
        score += 30.0
    if no_ten_llm_agents:
        score += 30.0
    return clamp_score(score)


def score_performance(
    median_throughput_trades_per_sec: float | None,
    median_latency_ms: float | None,
    failure_rate: float | None,
    thresholds: dict[str, float] | None = None,
) -> float:
    """Score performance dimension (0-100, weight 10%).

    thresholds: optional dict with keys 'min_throughput', 'max_latency_ms',
    'max_failure_rate'. Defaults: 100 trades/sec, 5000ms, 0.01 (1%).
    """
    thresholds = thresholds or {
        "min_throughput": 100.0,
        "max_latency_ms": 5000.0,
        "max_failure_rate": 0.01,
    }

    score = 100.0
    if (
        median_throughput_trades_per_sec is not None
        and median_throughput_trades_per_sec < thresholds["min_throughput"]
    ):
        score -= 33.0
    if median_latency_ms is not None and median_latency_ms > thresholds["max_latency_ms"]:
        score -= 33.0
    if failure_rate is not None and failure_rate > thresholds["max_failure_rate"]:
        score -= 34.0
    return clamp_score(score)


def check_disqualifiers(
    correctness_passed: bool,
    deterministic_risk_enforced: bool,
    critical_security_issue: bool,
    unacceptable_license: bool,
    unresolved_critical_integration_risk: bool,
    evidence_refs: dict[str, str] | None = None,
) -> tuple[tuple[Disqualifier, ...], bool]:
    """Check hard disqualifiers and mandatory gate status.

    Returns (disqualifiers, mandatory_gates_passed).
    """
    evidence_refs = evidence_refs or {}
    disqualifiers: list[Disqualifier] = []

    if not correctness_passed:
        disqualifiers.append(
            Disqualifier(
                name="mandatory_correctness_failure",
                reason="correctness gate failed — engine cannot produce correct fills",
                evidence_ref=evidence_refs.get("correctness", "engine assessment"),
            )
        )

    if not deterministic_risk_enforced:
        disqualifiers.append(
            Disqualifier(
                name="cannot_enforce_deterministic_risk",
                reason="engine cannot enforce Superbot deterministic risk rules",
                evidence_ref=evidence_refs.get("deterministic_risk", "engine assessment"),
            )
        )

    if critical_security_issue:
        disqualifiers.append(
            Disqualifier(
                name="unresolved_critical_security_issue",
                reason="critical security issue unresolved",
                evidence_ref=evidence_refs.get("security", "security scan"),
            )
        )

    if unacceptable_license:
        disqualifiers.append(
            Disqualifier(
                name="unacceptable_terms_license",
                reason="unacceptable terms or licence",
                evidence_ref=evidence_refs.get("license", "licence review"),
            )
        )

    mandatory_gates_passed = correctness_passed and deterministic_risk_enforced
    return tuple(disqualifiers), mandatory_gates_passed


def score_engine(
    engine: str,
    # Inputs from POC protocol (M3.2a)
    correctness_passed: bool = False,
    correctness_gate_passed_on_all_repetitions: bool = False,
    deterministic_replay_passed: bool = False,
    noise_rule_defined: bool = False,
    seed_fixed_datasets: bool = False,
    pass_rate: float = 0.0,
    median_latency_ms: float | None = None,
    # Inputs from benchmark (M3.6)
    peak_rss_mb: float | None = None,
    disk_io_mb: float | None = None,
    startup_ms: float | None = None,
    median_throughput_trades_per_sec: float | None = None,
    failure_rate: float | None = None,
    # Inputs from architecture/assessment
    deterministic_risk_enforced: bool = False,
    standard_contracts_used: bool = False,
    split_chronological_used: bool = False,
    stdlib_only: bool = False,
    versioned_configs: bool = False,
    no_ten_llm_agents: bool = False,
    # Disqualifier inputs
    critical_security_issue: bool = False,
    unacceptable_license: bool = False,
    unresolved_critical_integration_risk: bool = False,
    evidence_refs: dict[str, str] | None = None,
    resource_thresholds: dict[str, float] | None = None,
    performance_thresholds: dict[str, float] | None = None,
) -> EngineScoreResult:
    """Score a candidate engine across all weighted dimensions.

    Applies hard disqualifiers and determines qualification status.

    Args:
        engine: Engine identifier (e.g., "custom_baseline", "nautilus_trader", "lean").
        correctness_passed: Whether correctness gate passed.
        correctness_gate_passed_on_all_repetitions: Whether correctness passed on every repetition.
        deterministic_replay_passed: Whether deterministic replay produced identical results.
        noise_rule_defined: Whether noise rule is defined.
        seed_fixed_datasets: Whether fixed-seed datasets are used.
        pass_rate: POC pass rate (0-100).
        median_latency_ms: Median latency in ms.
        peak_rss_mb: Peak RSS memory in MB.
        disk_io_mb: Disk I/O in MB.
        startup_ms: Startup time in ms.
        median_throughput_trades_per_sec: Median throughput in trades/sec.
        failure_rate: Failure rate (0.0-1.0).
        deterministic_risk_enforced: Whether engine enforces deterministic risk.
        standard_contracts_used: Whether engine uses standard contracts.
        split_chronological_used: Whether chronological splits are used.
        stdlib_only: Whether engine code is stdlib-only.
        versioned_configs: Whether engine uses versioned configs.
        no_ten_llm_agents: Whether engine avoids ten separate LLM agents.
        critical_security_issue: Whether a critical security issue exists.
        unacceptable_license: Whether terms/licence are unacceptable.
        unresolved_critical_integration_risk: Whether critical integration risk remains unresolved.
        evidence_refs: Optional evidence references per disqualifier category.
        resource_thresholds: Optional resource efficiency thresholds.
        performance_thresholds: Optional performance thresholds.

    Returns:
        EngineScoreResult with total score, disqualifiers, and qualification status.
    """
    safety_correctness = score_safety_correctness(
        correctness_passed,
        correctness_gate_passed_on_all_repetitions,
        deterministic_risk_enforced,
    )
    compatibility = score_compatibility(
        deterministic_risk_enforced,
        standard_contracts_used,
        split_chronological_used,
    )
    reproducibility = score_reproducibility(
        deterministic_replay_passed,
        noise_rule_defined,
        seed_fixed_datasets,
    )
    resource_efficiency = score_resource_efficiency(
        peak_rss_mb, disk_io_mb, startup_ms, resource_thresholds
    )
    maintainability = score_maintainability(
        stdlib_only,
        versioned_configs,
        no_ten_llm_agents,
    )
    performance = score_performance(
        median_throughput_trades_per_sec,
        median_latency_ms,
        failure_rate,
        performance_thresholds,
    )

    score = EngineScore(
        engine=engine,
        safety_correctness=safety_correctness,
        compatibility=compatibility,
        reproducibility=reproducibility,
        resource_efficiency=resource_efficiency,
        maintainability=maintainability,
        performance=performance,
    )

    disqualifiers, mandatory_gates_passed = check_disqualifiers(
        correctness_passed,
        deterministic_risk_enforced,
        critical_security_issue,
        unacceptable_license,
        unresolved_critical_integration_risk,
        evidence_refs,
    )

    return EngineScoreResult(
        engine=engine,
        score=score,
        disqualifiers=disqualifiers,
        mandatory_gates_passed=mandatory_gates_passed,
        unresolved_critical_integration_risk=unresolved_critical_integration_risk,
    )


def compare_engines(results: list[EngineScoreResult]) -> EngineScoreResult | None:
    """Return the best qualified engine from scored results.

    Among qualified engines (is_qualified=True), returns the one with the
    highest total score. Returns None if no engine qualifies.
    """
    qualified = [r for r in results if r.is_qualified]
    if not qualified:
        return None
    return max(qualified, key=lambda r: r.total_score)