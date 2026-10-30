"""RED tests for M9.4 — Analyst, strategy proposer, reviewer and diagnostic/improvement roles.

Tests define:
- AnalystRole: analyzes market data, produces analysis reports
- StrategyProposerRole: proposes trading strategies based on analysis
- ReviewerRole: reviews strategy proposals, approves/rejects
- DiagnosticRole: diagnoses issues in strategies/runs
- ImprovementRole: suggests improvements based on diagnostics
- RoleRegistry: registry of agents and their roles
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.m9.agent_roles import (
    AnalystReport,
    AnalystRole,
    DiagnosticResult,
    DiagnosticRole,
    ImprovementRole,
    ImprovementSuggestion,
    ReviewerRole,
    ReviewResult,
    RoleRegistry,
    StrategyProposal,
    StrategyProposerRole,
    get_role,
    register_role,
)


def test_analyst_role_creates():
    """AnalystRole can be created with agent_id."""
    role = AnalystRole(agent_id="analyst_1")
    assert role.agent_id == "analyst_1"
    assert role.name == "analyst"


def test_analyst_report_creates():
    """AnalystReport stores all fields."""
    report = AnalystReport(
        analyst_id="analyst_1",
        market="EURUSD",
        trend="up",
        confidence=Decimal("0.85"),
        key_findings=["strong uptrend", "low volatility"],
    )
    assert report.analyst_id == "analyst_1"
    assert report.market == "EURUSD"
    assert report.trend == "up"
    assert report.confidence == Decimal("0.85")
    assert report.key_findings == ["strong uptrend", "low volatility"]


def test_analyst_role_uptrend():
    """Analyst detects uptrend when last price > 2% above first."""
    role = AnalystRole(agent_id="analyst_1")
    market_data = {
        "symbol": "EURUSD",
        "prices": [100.0, 101.0, 102.0, 103.0, 105.0],
    }
    report = role.analyze(market_data)
    assert report.market == "EURUSD"
    assert report.trend == "up"
    assert report.confidence == Decimal("0.85")


def test_analyst_role_downtrend():
    """Analyst detects downtrend when last price < 2% below first."""
    role = AnalystRole(agent_id="analyst_1")
    market_data = {
        "symbol": "GBPUSD",
        "prices": [100.0, 99.0, 98.0, 97.0, 96.0],
    }
    report = role.analyze(market_data)
    assert report.market == "GBPUSD"
    assert report.trend == "down"
    assert report.confidence == Decimal("0.85")


def test_analyst_role_ranging():
    """Analyst detects ranging when price change within 2%."""
    role = AnalystRole(agent_id="analyst_1")
    market_data = {
        "symbol": "USDJPY",
        "prices": [100.0, 100.5, 100.2, 100.3],
    }
    report = role.analyze(market_data)
    assert report.trend == "ranging"
    assert report.confidence == Decimal("0.60")


def test_analyst_role_insufficient_data():
    """Analyst returns ranging with low confidence when < 2 prices."""
    role = AnalystRole(agent_id="analyst_1")
    market_data = {"symbol": "EURUSD", "prices": [100.0]}
    report = role.analyze(market_data)
    assert report.trend == "ranging"
    assert report.confidence == Decimal("0.5")


def test_strategy_proposer_role_creates():
    """StrategyProposerRole can be created."""
    role = StrategyProposerRole(agent_id="proposer_1")
    assert role.agent_id == "proposer_1"
    assert role.name == "strategy_proposer"


def test_strategy_proposal_creates():
    """StrategyProposal stores all fields."""
    proposal = StrategyProposal(
        proposal_id="prop_1",
        proposer_id="proposer_1",
        strategy_name="trend_following",
        parameters={"window": 20},
        expected_return=Decimal("0.15"),
        max_drawdown=Decimal("0.05"),
    )
    assert proposal.proposal_id == "prop_1"
    assert proposal.proposer_id == "proposer_1"
    assert proposal.strategy_name == "trend_following"
    assert proposal.expected_return == Decimal("0.15")
    assert proposal.max_drawdown == Decimal("0.05")


def test_strategy_proposer_proposes():
    """StrategyProposerRole proposes a strategy from analysis."""
    proposer = StrategyProposerRole(agent_id="proposer_1")
    analysis = {
        "strategy": "trend_following",
        "parameters": {"window": 20},
        "expected_return": "0.15",
        "max_drawdown": "0.05",
    }
    proposal = proposer.propose(analysis)
    assert proposal.proposer_id == "proposer_1"
    assert proposal.strategy_name == "trend_following"
    assert proposal.expected_return == Decimal("0.15")
    assert proposal.max_drawdown == Decimal("0.05")


def test_reviewer_role_creates():
    """ReviewerRole can be created."""
    role = ReviewerRole(agent_id="reviewer_1")
    assert role.agent_id == "reviewer_1"
    assert role.name == "reviewer"


def test_review_result_creates():
    """ReviewResult stores all fields."""
    result = ReviewResult(
        reviewer_id="reviewer_1",
        proposal_id="prop_1",
        approved=True,
        reasons=["good strategy"],
    )
    assert result.reviewer_id == "reviewer_1"
    assert result.proposal_id == "prop_1"
    assert result.approved is True


def test_reviewer_approves_good_proposal():
    """Reviewer approves proposal meeting all thresholds."""
    reviewer = ReviewerRole(agent_id="reviewer_1")
    proposal = {
        "strategy_name": "trend_follow",
        "expected_return": Decimal("0.15"),
        "max_drawdown": Decimal("0.05"),
    }
    result = reviewer.review(proposal)
    assert result.approved is True
    assert result.reasons == []


def test_reviewer_rejects_low_return():
    """Reviewer rejects proposal with expected_return below 0.05."""
    reviewer = ReviewerRole(agent_id="reviewer_1")
    proposal = {
        "strategy_name": "bad_strategy",
        "expected_return": Decimal("0.02"),
        "max_drawdown": Decimal("0.05"),
    }
    result = reviewer.review(proposal)
    assert result.approved is False
    assert any("expected_return" in r for r in result.reasons)


def test_reviewer_rejects_high_drawdown():
    """Reviewer rejects proposal with max_drawdown above 0.20."""
    reviewer = ReviewerRole(agent_id="reviewer_1")
    proposal = {
        "strategy_name": "risky_strategy",
        "expected_return": Decimal("0.15"),
        "max_drawdown": Decimal("0.25"),
    }
    result = reviewer.review(proposal)
    assert result.approved is False
    assert any("max_drawdown" in r for r in result.reasons)


def test_reviewer_rejects_poor_risk_adjusted():
    """Reviewer rejects low return with high drawdown."""
    reviewer = ReviewerRole(agent_id="reviewer_1")
    proposal = {
        "strategy_name": "poor_risk",
        "expected_return": Decimal("0.08"),
        "max_drawdown": Decimal("0.15"),
    }
    result = reviewer.review(proposal)
    assert result.approved is False
    assert len(result.reasons) >= 1


def test_diagnostic_role_creates():
    """DiagnosticRole can be created."""
    role = DiagnosticRole(agent_id="diagnostic_1")
    assert role.agent_id == "diagnostic_1"
    assert role.name == "diagnostic"


def test_diagnostic_result_creates():
    """DiagnosticResult stores all fields."""
    result = DiagnosticResult(
        diagnostician_id="diagnostic_1",
        strategy_name="trend_follow",
        issues=["win_rate below 40% threshold"],
        recommendations=["review entry criteria"],
    )
    assert result.diagnostician_id == "diagnostic_1"
    assert result.strategy_name == "trend_follow"


def test_diagnostic_diagnoses_issues():
    """DiagnosticRole diagnoses win rate, drawdown, return issues."""
    diagnostician = DiagnosticRole(agent_id="diagnostic_1")
    performance = {
        "strategy_name": "trend_follow",
        "win_rate": "0.35",
        "max_dd": "0.15",
        "avg_return": "0.02",
    }
    result = diagnostician.diagnose(performance)
    assert result.diagnostician_id == "diagnostic_1"
    assert result.strategy_name == "trend_follow"
    assert any("win_rate" in i for i in result.issues)
    assert any("drawdown" in i for i in result.issues)
    assert any("avg_return" in i for i in result.issues)
    assert len(result.recommendations) > 0


def test_diagnostic_no_issues():
    """Diagnostic reports no significant issues when metrics are fine."""
    diagnostician = DiagnosticRole(agent_id="diagnostic_1")
    performance = {
        "strategy_name": "good_strategy",
        "win_rate": "0.60",
        "max_dd": "0.05",
        "avg_return": "0.10",
    }
    result = diagnostician.diagnose(performance)
    assert len(result.issues) == 1
    assert "no significant issues detected" in result.issues[0]


def test_improvement_role_creates():
    """ImprovementRole can be created."""
    role = ImprovementRole(agent_id="improver_1")
    assert role.agent_id == "improver_1"
    assert role.name == "improver"


def test_improvement_suggestion_creates():
    """ImprovementSuggestion stores all fields."""
    suggestion = ImprovementSuggestion(
        suggestion_id="suggestion_1",
        strategy_name="trend_follow",
        area="risk_management",
        suggestion="reduce position size",
        expected_improvement=Decimal("0.15"),
    )
    assert suggestion.strategy_name == "trend_follow"
    assert suggestion.area == "risk_management"


def test_improvement_drawdown_area():
    """Improvement suggests risk_management for drawdown issues."""
    improver = ImprovementRole(agent_id="improver_1")
    diagnosis = {
        "strategy_name": "trend_follow",
        "issues": ["max_drawdown exceeds 10% threshold"],
    }
    result = improver.improve(diagnosis)
    assert result.strategy_name == "trend_follow"
    assert result.area == "risk_management"


def test_improvement_win_rate_area():
    """Improvement suggests entry_timing for win_rate issues."""
    improver = ImprovementRole(agent_id="improver_1")
    diagnosis = {
        "strategy_name": "trend_follow",
        "issues": ["win_rate below 40% threshold"],
    }
    result = improver.improve(diagnosis)
    assert result.area == "entry_timing"


def test_improvement_return_area():
    """Improvement suggests position_sizing for return issues."""
    improver = ImprovementRole(agent_id="improver_1")
    diagnosis = {
        "strategy_name": "trend_follow",
        "issues": ["avg_return below 5% threshold"],
    }
    result = improver.improve(diagnosis)
    assert result.area == "position_sizing"


def test_role_registry_creates():
    """RoleRegistry can be created."""
    registry = RoleRegistry()
    assert registry is not None


def test_register_role():
    """register_role adds a role to the registry."""
    registry = RoleRegistry()
    role = AnalystRole(agent_id="analyst_1")
    registry.register_role("analyst", role)
    assert registry.get_role("analyst") == role


def test_get_unknown_role():
    """get_role returns None for unknown role."""
    registry = RoleRegistry()
    assert registry.get_role("nonexistent") is None


def test_deterministic_analyst():
    """Same inputs yield identical analyst reports."""
    s1 = AnalystRole(agent_id="analyst_1")
    s2 = AnalystRole(agent_id="analyst_1")
    data = {"symbol": "EURUSD", "prices": [100.0, 101.0, 102.0]}
    r1 = s1.analyze(data)
    r2 = s2.analyze(data)
    assert r1.trend == r2.trend
    assert r1.confidence == r2.confidence
    assert r1.key_findings == r2.key_findings


def test_register_role_function():
    """register_role convenience function works."""
    registry = RoleRegistry()
    role = AnalystRole(agent_id="analyst_1")
    register_role(registry, "analyst", role)
    assert registry.get_role("analyst") == role


def test_get_role_function():
    """get_role convenience function works."""
    registry = RoleRegistry()
    role = AnalystRole(agent_id="analyst_1")
    register_role(registry, "analyst", role)
    assert get_role(registry, "analyst") == role
