"""Portfolio/strategy/correlation-group risk service (schema.md section 7.1).

Deterministic portfolio risk service:
- Registers strategies with per-strategy risk limits (max DD, daily loss, position size)
- Groups strategies into correlation groups with group-level DD caps
- Checks proposed trades against strategy and group limits
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskLimit:
    """Per-strategy risk limits, all Decimal."""

    max_dd_pct: Decimal
    daily_loss_pct: Decimal
    max_position_pct: Decimal


@dataclass(frozen=True)
class RiskCheckResult:
    """Risk check result."""

    allowed: bool
    reasons: list[str]


class StrategyRecord:
    """Registered strategy with its risk limit."""

    def __init__(
        self,
        name: str,
        limit: RiskLimit,
    ) -> None:
        self.name = name
        self.limit = limit
        self.current_dd_pct: Decimal = Decimal(0)
        self.daily_loss_pct: Decimal = Decimal(0)


class CorrelationGroup:
    """Groups strategies by correlation, enforces group-level DD cap."""

    def __init__(
        self,
        name: str,
        max_group_dd_pct: Decimal,
    ) -> None:
        self.name = name
        self.max_group_dd_pct = max_group_dd_pct
        self.strategies: list[str] = []

    def add_strategy(self, strategy_name: str) -> None:
        """Add a strategy to this group."""
        if strategy_name not in self.strategies:
            self.strategies.append(strategy_name)


def register_strategy(
    service: PortfolioRiskService,
    name: str,
    max_dd_pct: Decimal,
    daily_loss_pct: Decimal,
    max_position_pct: Decimal = Decimal(5),
) -> None:
    """Register a strategy with risk limits on a PortfolioRiskService."""
    service.register_strategy(
        name=name,
        max_dd_pct=max_dd_pct,
        daily_loss_pct=daily_loss_pct,
        max_position_pct=max_position_pct,
    )


class PortfolioRiskService:
    """Tracks portfolio risk across strategies and correlation groups."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyRecord] = {}
        self._groups: dict[str, CorrelationGroup] = {}

    def register_strategy(
        self,
        name: str,
        max_dd_pct: Decimal,
        daily_loss_pct: Decimal,
        max_position_pct: Decimal = Decimal(5),
    ) -> None:
        """Register a strategy with risk limits."""
        self._strategies[name] = StrategyRecord(
            name=name,
            limit=RiskLimit(
                max_dd_pct=max_dd_pct,
                daily_loss_pct=daily_loss_pct,
                max_position_pct=max_position_pct,
            ),
        )

    def get_strategy(self, name: str) -> StrategyRecord | None:
        """Get a registered strategy by name."""
        return self._strategies.get(name)

    def create_group(
        self,
        name: str,
        max_group_dd_pct: Decimal,
    ) -> CorrelationGroup:
        """Create a correlation group."""
        group = CorrelationGroup(name=name, max_group_dd_pct=max_group_dd_pct)
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> CorrelationGroup | None:
        """Get a correlation group by name."""
        return self._groups.get(name)


def check_strategy_risk(
    current_dd_pct: Decimal,
    daily_loss_pct: Decimal,
    limit: RiskLimit,
) -> RiskCheckResult:
    """Check strategy risk against limits.

    Args:
        current_dd_pct: current drawdown percentage
        daily_loss_pct: current daily loss percentage
        limit: RiskLimit thresholds

    Returns RiskCheckResult with allowed flag and failure reasons.
    """
    reasons: list[str] = []
    allowed = True

    if current_dd_pct > limit.max_dd_pct:
        reasons.append(f"max_dd_pct {current_dd_pct} exceeds limit {limit.max_dd_pct}")
        allowed = False

    if daily_loss_pct > limit.daily_loss_pct:
        reasons.append(f"daily_loss_pct {daily_loss_pct} exceeds limit {limit.daily_loss_pct}")
        allowed = False

    return RiskCheckResult(
        allowed=allowed,
        reasons=reasons,
    )


def check_group_risk(
    group_dd_pct: Decimal,
    limit: Decimal,
) -> RiskCheckResult:
    """Check correlation group risk against DD cap.

    Args:
        group_dd_pct: current group drawdown percentage
        limit: maximum group DD percentage

    Returns RiskCheckResult with allowed flag and failure reasons.
    """
    reasons: list[str] = []
    allowed = True

    if group_dd_pct > limit:
        reasons.append(f"group_dd_pct {group_dd_pct} exceeds group limit {limit}")
        allowed = False

    return RiskCheckResult(
        allowed=allowed,
        reasons=reasons,
    )


def update_strategy_pnl(
    service: PortfolioRiskService,
    name: str,
    dd_pct: Decimal,
    daily_loss_pct: Decimal,
) -> None:
    """Update a strategy's current DD and daily loss."""
    record = service.get_strategy(name)
    if record is not None:
        record.current_dd_pct = dd_pct
        record.daily_loss_pct = daily_loss_pct
