"""M9.4 — Analyst, strategy proposer, reviewer and diagnostic/improvement roles.

Deterministic role-based agent system:
- AnalystRole: analyzes market data, produces analysis reports
- StrategyProposerRole: proposes trading strategies based on analysis
- ReviewerRole: reviews strategy proposals, approves/rejects
- DiagnosticRole: diagnoses issues in strategies/runs
- ImprovementRole: suggests improvements based on diagnostics
- RoleRegistry: registry of agents and their roles
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AnalystReport:
    """Result of analyst analysis."""

    analyst_id: str
    market: str
    trend: str  # "up", "down", "ranging"
    confidence: Decimal
    key_findings: list[str]


@dataclass(frozen=True)
class AnalystRole:
    """Analyzes market data and produces analysis reports."""

    agent_id: str
    name: str = "analyst"

    def analyze(self, market_data: dict) -> AnalystReport:
        """Analyze market data and produce an analysis report."""
        symbol = market_data.get("symbol", "unknown")
        prices = market_data.get("prices", [])

        if len(prices) < 2:
            trend = "ranging"
            confidence = Decimal("0.5")
            findings = ["insufficient data for trend analysis"]
        else:
            first_price = Decimal(str(prices[0]))
            last_price = Decimal(str(prices[-1]))
            if last_price > first_price * Decimal("1.02"):
                trend = "up"
                confidence = Decimal("0.85")
                findings = ["strong uptrend detected"]
            elif last_price < first_price * Decimal("0.98"):
                trend = "down"
                confidence = Decimal("0.85")
                findings = ["strong downtrend detected"]
            else:
                trend = "ranging"
                confidence = Decimal("0.60")
                findings = ["market ranging, no clear trend"]

        return AnalystReport(
            analyst_id=self.agent_id,
            market=symbol,
            trend=trend,
            confidence=confidence,
            key_findings=findings,
        )


@dataclass(frozen=True)
class StrategyProposal:
    """A proposed trading strategy."""

    proposal_id: str
    proposer_id: str
    strategy_name: str
    parameters: dict
    expected_return: Decimal
    max_drawdown: Decimal


@dataclass(frozen=True)
class StrategyProposerRole:
    """Proposes trading strategies based on analysis."""

    agent_id: str
    name: str = "strategy_proposer"

    def propose(self, analysis: dict) -> StrategyProposal:
        """Propose a strategy based on analysis results."""
        strategy_name = analysis.get("strategy", "trend_following")
        params = analysis.get("parameters", {})
        expected_return = Decimal(str(analysis.get("expected_return", "0.10")))
        max_drawdown = Decimal(str(analysis.get("max_drawdown", "0.10")))

        return StrategyProposal(
            proposal_id=f"prop_{self.agent_id}_{hash(str(analysis)) % 10000}",
            proposer_id=self.agent_id,
            strategy_name=strategy_name,
            parameters=dict(params),
            expected_return=expected_return,
            max_drawdown=max_drawdown,
        )


@dataclass(frozen=True)
class ReviewResult:
    """Result of reviewing a strategy proposal."""

    reviewer_id: str
    proposal_id: str
    approved: bool
    reasons: list[str]


class ReviewerRole:
    """Reviews strategy proposals and decides approve/reject."""

    def __init__(self, agent_id: str, name: str = "reviewer") -> None:
        self.agent_id = agent_id
        self.name = name

    def review(self, proposal: dict) -> ReviewResult:
        """Review a strategy proposal and return a result."""
        strategy_name = proposal.get("strategy_name", "unknown")
        expected_return = Decimal(str(proposal.get("expected_return", "0")))
        max_drawdown = Decimal(str(proposal.get("max_drawdown", "1.0")))

        reasons: list[str] = []
        qualified = True

        if expected_return < Decimal("0.05"):
            reasons.append(f"expected_return {expected_return} below minimum 0.05")
            qualified = False

        if max_drawdown > Decimal("0.20"):
            reasons.append(f"max_drawdown {max_drawdown} above maximum 0.20")
            qualified = False

        if expected_return < Decimal("0.10") and max_drawdown > Decimal("0.10"):
            reasons.append(
                f"poor risk-adjusted return: return {expected_return} too low for drawdown {max_drawdown}"
            )
            qualified = False

        return ReviewResult(
            reviewer_id=self.agent_id,
            proposal_id=strategy_name,
            approved=qualified,
            reasons=reasons,
        )


@dataclass(frozen=True)
class DiagnosticResult:
    """Result of diagnostic analysis."""

    diagnostician_id: str
    strategy_name: str
    issues: list[str]
    recommendations: list[str]


class DiagnosticRole:
    """Diagnoses issues in strategy performance."""

    def __init__(self, agent_id: str, name: str = "diagnostic") -> None:
        self.agent_id = agent_id
        self.name = name

    def diagnose(self, performance: dict) -> DiagnosticResult:
        """Diagnose strategy performance issues."""
        strategy_name = performance.get("strategy_name", "unknown")
        win_rate = Decimal(str(performance.get("win_rate", "0.5")))
        max_dd = Decimal(str(performance.get("max_dd", "0.0")))
        avg_return = Decimal(str(performance.get("avg_return", "0.0")))

        issues: list[str] = []
        recommendations: list[str] = []

        if win_rate < Decimal("0.40"):
            issues.append(f"win_rate {win_rate} below 40% threshold")
            recommendations.append("review entry criteria and improve signal quality")

        if max_dd > Decimal("0.10"):
            issues.append(f"max_drawdown {max_dd} exceeds 10% threshold")
            recommendations.append("reduce position size and add stop-loss")

        if avg_return < Decimal("0.05"):
            issues.append(f"avg_return {avg_return} below 5% threshold")
            recommendations.append("increase position size or improve entry timing")

        if not issues:
            issues.append("no significant issues detected")
            recommendations.append("maintain current strategy parameters")

        return DiagnosticResult(
            diagnostician_id=self.agent_id,
            strategy_name=strategy_name,
            issues=issues,
            recommendations=recommendations,
        )


@dataclass(frozen=True)
class ImprovementSuggestion:
    """A suggested improvement for a strategy."""

    suggestion_id: str
    strategy_name: str
    area: str
    suggestion: str
    expected_improvement: Decimal


class ImprovementRole:
    """Suggests improvements based on diagnostic results."""

    def __init__(self, agent_id: str, name: str = "improver") -> None:
        self.agent_id = agent_id
        self.name = name

    def improve(self, diagnosis: dict) -> ImprovementSuggestion:
        """Generate improvement suggestions based on diagnosis."""
        strategy_name = diagnosis.get("strategy_name", "unknown")
        issues = diagnosis.get("issues", [])

        if "drawdown" in str(issues).lower():
            area = "risk_management"
            suggestion = "reduce position size and add stop-loss orders"
            expected_improvement = Decimal("0.15")
        elif "win_rate" in str(issues).lower():
            area = "entry_timing"
            suggestion = "improve entry signal quality and add confirmation filters"
            expected_improvement = Decimal("0.10")
        elif "return" in str(issues).lower():
            area = "position_sizing"
            suggestion = "increase position size on high-conviction setups"
            expected_improvement = Decimal("0.08")
        else:
            area = "general"
            suggestion = "maintain current parameters and monitor performance"
            expected_improvement = Decimal("0.02")

        return ImprovementSuggestion(
            suggestion_id=f"suggestion_{self.agent_id}_{strategy_name}_{area}",
            strategy_name=strategy_name,
            area=area,
            suggestion=suggestion,
            expected_improvement=expected_improvement,
        )


class RoleRegistry:
    """Registry of agents and their roles."""

    def __init__(self) -> None:
        self._roles: dict[str, object] = {}

    def register_role(self, role_name: str, role: object) -> None:
        """Register a role by name."""
        self._roles[role_name] = role

    def get_role(self, role_name: str) -> object | None:
        """Get a role by name."""
        return self._roles.get(role_name)


def register_role(
    registry: RoleRegistry,
    role_name: str,
    role: object,
) -> None:
    """Register a role (convenience function)."""
    registry.register_role(role_name, role)


def get_role(
    registry: RoleRegistry,
    role_name: str,
) -> object | None:
    """Get a role by name (convenience function)."""
    return registry.get_role(role_name)
