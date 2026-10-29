"""Combined open-risk cap 5%; adaptive risk and verified sizing (schema.md section 7.3).

Deterministic open-risk service:
- Tracks combined open risk across all strategies and positions
- Combined open-risk cap: 5% of portfolio; blocks new entries when exceeded
- Adaptive risk: position sizing scales to available headroom
- Verified sizing: position size verified against open-risk cap before entry
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PositionRisk:
    """Risk of a single open position."""

    strategy_name: str
    symbol: str
    notional_usd: Decimal
    risk_pct: Decimal


@dataclass(frozen=True)
class OpenRiskResult:
    """Combined open-risk check result."""

    combined_open_risk_pct: Decimal
    cap_pct: Decimal
    headroom_pct: Decimal
    allowed: bool
    reasons: list[str]


def register_open_position(
    service: OpenRiskService,
    strategy_name: str,
    symbol: str,
    notional_usd: Decimal,
    risk_pct: Decimal,
) -> None:
    """Register an open position with its risk percentage on an OpenRiskService."""
    service.register_open_position(
        strategy_name=strategy_name,
        symbol=symbol,
        notional_usd=notional_usd,
        risk_pct=risk_pct,
    )


def remove_open_position(
    service: OpenRiskService,
    strategy_name: str,
    symbol: str,
) -> None:
    """Remove an open position from an OpenRiskService."""
    service.remove_open_position(strategy_name=strategy_name, symbol=symbol)


def check_combined_open_risk(
    combined_open_risk_pct: Decimal,
    cap_pct: Decimal,
) -> OpenRiskResult:
    """Check combined open risk against cap."""
    headroom = cap_pct - combined_open_risk_pct
    reasons: list[str] = []
    allowed = combined_open_risk_pct <= cap_pct
    if not allowed:
        reasons.append(f"combined_open_risk {combined_open_risk_pct} exceeds cap {cap_pct}")
    return OpenRiskResult(
        combined_open_risk_pct=combined_open_risk_pct,
        cap_pct=cap_pct,
        headroom_pct=headroom,
        allowed=allowed,
        reasons=reasons,
    )


def compute_adaptive_size(
    service: OpenRiskService,
    requested_size: Decimal,
    cap_pct: Decimal,
) -> Decimal:
    """Compute adaptive position size based on available headroom."""
    return verified_size(service, requested_size, cap_pct)


def verified_size(
    service: OpenRiskService,
    requested_size_pct: Decimal,
    cap_pct: Decimal,
) -> Decimal:
    """Verify position size against open-risk cap."""
    headroom = service.headroom_pct()
    if headroom <= Decimal(0):
        return Decimal(0)
    return min(requested_size_pct, headroom)


class OpenRiskService:
    """Tracks combined open risk across all strategies and positions."""

    def __init__(
        self,
        combined_open_risk_cap_pct: Decimal = Decimal(5),
    ) -> None:
        self.combined_open_risk_cap_pct = combined_open_risk_cap_pct
        self._positions: dict[tuple[str, str], PositionRisk] = {}

    def register_open_position(
        self,
        strategy_name: str,
        symbol: str,
        notional_usd: Decimal,
        risk_pct: Decimal,
    ) -> None:
        """Register an open position with its risk percentage."""
        self._positions[(strategy_name, symbol)] = PositionRisk(
            strategy_name=strategy_name,
            symbol=symbol,
            notional_usd=notional_usd,
            risk_pct=risk_pct,
        )

    def remove_open_position(self, strategy_name: str, symbol: str) -> None:
        """Remove an open position."""
        self._positions.pop((strategy_name, symbol), None)

    def get_position(self, strategy_name: str, symbol: str) -> PositionRisk | None:
        """Get an open position by strategy and symbol."""
        return self._positions.get((strategy_name, symbol))

    @property
    def combined_open_risk_pct(self) -> Decimal:
        """Total open risk percentage across all positions."""
        return sum((p.risk_pct for p in self._positions.values()), Decimal(0))

    def headroom_pct(self) -> Decimal:
        """Available risk headroom = cap - combined open risk."""
        return self.combined_open_risk_cap_pct - self.combined_open_risk_pct
