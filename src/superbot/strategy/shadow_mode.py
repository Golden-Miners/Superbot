"""Shadow mode evaluation (schema.md section 6.7).

Deterministic shadow-mode eligibility check:
- Configurable opportunity count, elapsed time, and data-quality conditions
- All conditions must pass for shadow mode to be eligible
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ShadowConfig:
    """Configurable shadow-mode conditions."""

    min_opportunities: int = 10
    min_elapsed_minutes: int = 60
    min_data_quality_pct: Decimal = Decimal(90)


@dataclass(frozen=True)
class ShadowResult:
    """Shadow-mode eligibility result."""

    eligible: bool
    opportunity_count: int
    elapsed_minutes: int
    data_quality_pct: Decimal
    reasons: list[str]


class ShadowModeEvaluator:
    """Evaluates shadow-mode eligibility."""

    def evaluate(
        self,
        opportunity_count: int,
        elapsed_minutes: int,
        data_quality_pct: Decimal,
        config: ShadowConfig | None = None,
    ) -> ShadowResult:
        """Evaluate shadow-mode eligibility against config.

        Args:
            opportunity_count: number of trading opportunities observed
            elapsed_minutes: minutes of observation elapsed
            data_quality_pct: data completeness/quality percentage
            config: ShadowConfig (defaults to ShadowConfig())

        Returns ShadowResult with eligible flag and failure reasons.
        """
        if config is None:
            config = ShadowConfig()

        reasons: list[str] = []
        eligible = True

        if opportunity_count < config.min_opportunities:
            reasons.append(
                f"opportunity_count {opportunity_count} below minimum {config.min_opportunities}"
            )
            eligible = False

        if elapsed_minutes < config.min_elapsed_minutes:
            reasons.append(
                f"elapsed_minutes {elapsed_minutes} below minimum {config.min_elapsed_minutes}"
            )
            eligible = False

        if data_quality_pct < config.min_data_quality_pct:
            reasons.append(
                f"data_quality_pct {data_quality_pct} below minimum {config.min_data_quality_pct}"
            )
            eligible = False

        return ShadowResult(
            eligible=eligible,
            opportunity_count=opportunity_count,
            elapsed_minutes=elapsed_minutes,
            data_quality_pct=data_quality_pct,
            reasons=reasons,
        )


def shadow_mode_eligible(
    opportunity_count: int,
    elapsed_minutes: int,
    data_quality_pct: Decimal,
    config: ShadowConfig | None = None,
) -> ShadowResult:
    """Check shadow-mode eligibility.

    Convenience wrapper around ShadowModeEvaluator.evaluate.
    """
    return ShadowModeEvaluator().evaluate(
        opportunity_count=opportunity_count,
        elapsed_minutes=elapsed_minutes,
        data_quality_pct=data_quality_pct,
        config=config,
    )


def evaluate_shadow_mode(
    opportunity_count: int,
    elapsed_minutes: int,
    data_quality_pct: Decimal,
    config: ShadowConfig | None = None,
) -> ShadowResult:
    """Evaluate shadow-mode eligibility (alias for shadow_mode_eligible)."""
    return shadow_mode_eligible(
        opportunity_count=opportunity_count,
        elapsed_minutes=elapsed_minutes,
        data_quality_pct=data_quality_pct,
        config=config,
    )
