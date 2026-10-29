"""Internal-simulation eligibility and version archive rule (schema.md section 6.8).

Deterministic internal-simulation eligibility check:
- Cost-adjusted return %, Sharpe, max DD against configurable thresholds
- Three-failed-validation-attempt version archive rule
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class InternalSimulationConfig:
    """Configurable internal-simulation eligibility criteria."""

    min_cost_adjusted_return_pct: Decimal = Decimal(5)
    min_sharpe: Decimal = Decimal("1.0")
    max_max_dd_pct: Decimal = Decimal(15)
    max_validation_failures: int = 3


@dataclass(frozen=True)
class InternalSimulationResult:
    """Internal-simulation eligibility result."""

    eligible: bool
    cost_adjusted_return_pct: Decimal
    sharpe: Decimal
    max_dd_pct: Decimal
    reasons: list[str]


@dataclass(frozen=True)
class VersionArchiveRule:
    """Tracks validation attempts and archives after max failures."""

    max_failures: int = 3
    failures: dict[str, int] = field(default_factory=dict)
    archived: set[str] = field(default_factory=set)

    def is_archived(self, version_id: str) -> bool:
        """Check if a version has been archived."""
        return version_id in self.archived


class InternalSimulationEvaluator:
    """Evaluates internal-simulation eligibility against config."""

    def evaluate(
        self,
        cost_adjusted_return_pct: Decimal,
        sharpe: Decimal,
        max_dd_pct: Decimal,
        config: InternalSimulationConfig | None = None,
    ) -> InternalSimulationResult:
        """Evaluate internal-simulation eligibility against config.

        Args:
            cost_adjusted_return_pct: cost-adjusted return percentage
            sharpe: Sharpe ratio
            max_dd_pct: maximum drawdown percentage
            config: InternalSimulationConfig (defaults to InternalSimulationConfig())

        Returns InternalSimulationResult with eligible flag and failure reasons.
        """
        if config is None:
            config = InternalSimulationConfig()

        reasons: list[str] = []
        eligible = True

        if cost_adjusted_return_pct < config.min_cost_adjusted_return_pct:
            reasons.append(
                f"cost_adjusted_return_pct {cost_adjusted_return_pct} below minimum {config.min_cost_adjusted_return_pct}"
            )
            eligible = False

        if sharpe < config.min_sharpe:
            reasons.append(f"sharpe {sharpe} below minimum {config.min_sharpe}")
            eligible = False

        if max_dd_pct > config.max_max_dd_pct:
            reasons.append(f"max_dd_pct {max_dd_pct} above maximum {config.max_max_dd_pct}")
            eligible = False

        return InternalSimulationResult(
            eligible=eligible,
            cost_adjusted_return_pct=cost_adjusted_return_pct,
            sharpe=sharpe,
            max_dd_pct=max_dd_pct,
            reasons=reasons,
        )


class VersionArchiveManager:
    """Manages version archive rules across multiple versions."""

    def __init__(self) -> None:
        self._rules: dict[str, VersionArchiveRule] = {}

    def get_rule(self, version_id: str) -> VersionArchiveRule:
        """Get or create a rule for a version."""
        if version_id not in self._rules:
            self._rules[version_id] = VersionArchiveRule()
        return self._rules[version_id]

    def record_validation_attempt(self, version_id: str, passed: bool) -> None:
        """Record a validation attempt for a version."""
        rule = self.get_rule(version_id)
        if version_id in rule.archived:
            return
        if not passed:
            current = rule.failures.get(version_id, 0)
            rule.failures[version_id] = current + 1
            if rule.failures[version_id] >= rule.max_failures:
                rule.archived.add(version_id)

    def is_archived(self, version_id: str) -> bool:
        """Check if a version has been archived."""
        rule = self.get_rule(version_id)
        return version_id in rule.archived


def evaluate_internal_simulation_eligibility(
    cost_adjusted_return_pct: Decimal,
    sharpe: Decimal,
    max_dd_pct: Decimal,
    config: InternalSimulationConfig | None = None,
) -> InternalSimulationResult:
    """Check internal-simulation eligibility.

    Convenience wrapper around InternalSimulationEvaluator.evaluate.
    """
    return InternalSimulationEvaluator().evaluate(
        cost_adjusted_return_pct=cost_adjusted_return_pct,
        sharpe=sharpe,
        max_dd_pct=max_dd_pct,
        config=config,
    )


def record_validation_attempt(
    rule: VersionArchiveRule,
    version_id: str,
    passed: bool,
) -> None:
    """Record a validation attempt for a version on a VersionArchiveRule.

    Args:
        rule: VersionArchiveRule to record against
        version_id: version identifier
        passed: whether the validation passed
    """
    if version_id in rule.archived:
        return
    if passed:
        rule.failures[version_id] = 0
        return
    current = rule.failures.get(version_id, 0)
    rule.failures[version_id] = current + 1
    if rule.failures[version_id] >= rule.max_failures:
        rule.archived.add(version_id)


def is_version_archived(
    rule: VersionArchiveRule,
    version_id: str,
) -> bool:
    """Check if a version has been archived on a VersionArchiveRule."""
    return version_id in rule.archived
