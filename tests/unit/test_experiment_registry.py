"""RED tests for M8.4 — Experiment registry/data-code-strategy-parameter-cost-config refs.

Tests define:
- ExperimentRegistry: registry linking experiments to code, strategy, parameters, cost, config
- ExperimentRef: reference from an experiment to its code/config/strategy/parameter/cost artifacts
- Registry lookup by experiment id, code hash, strategy id
- Register an experiment with all its refs (data, code, strategy, parameter, cost, config)
- Lookup all artifacts for an experiment
- Lookup all experiments using a given code version or strategy
- Missing refs return None rather than crashing
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/DB activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.persistence.experiment_registry import (
    CodeRef,
    ConfigRef,
    CostRef,
    ExperimentRef,
    ExperimentRegistry,
    ParameterRef,
    StrategyRef,
)


def test_experiment_registry_creates():
    """ExperimentRegistry can be created."""
    registry = ExperimentRegistry()
    assert registry is not None


def test_register_experiment():
    """register_experiment stores experiment refs."""
    registry = ExperimentRegistry()
    ref = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    registry.register_experiment(ref)
    assert registry.get_experiment("exp_1") is not None


def test_get_experiment_refs():
    """get_experiment_refs returns all refs for an experiment."""
    registry = ExperimentRegistry()
    ref = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    registry.register_experiment(ref)
    result = registry.get_experiment("exp_1")
    assert result is not None
    assert result.code.commit == "abc123"
    assert result.strategy.name == "trend_follow"
    assert result.parameters.window == 20
    assert result.cost.spread == Decimal("0.1")
    assert result.config.env == "prod"


def test_get_unknown_experiment():
    """get_experiment returns None for unknown id."""
    registry = ExperimentRegistry()
    assert registry.get_experiment("nonexistent") is None


def test_find_experiments_by_code():
    """find_experiments_by_code returns experiments using a given code version."""
    registry = ExperimentRegistry()
    ref1 = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    ref2 = ExperimentRef(
        experiment_id="exp_2",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="structure_liq", version="v1"),
        parameters=ParameterRef(window=50, threshold=Decimal("0.3")),
        cost=CostRef(spread=Decimal("0.2"), commission=Decimal("0.1")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    registry.register_experiment(ref1)
    registry.register_experiment(ref2)
    results = registry.find_experiments_by_code("abc123")
    assert len(results) == 2
    assert "exp_1" in results
    assert "exp_2" in results


def test_find_experiments_by_strategy():
    """find_experiments_by_strategy returns experiments using a given strategy."""
    registry = ExperimentRegistry()
    ref1 = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    ref2 = ExperimentRef(
        experiment_id="exp_2",
        code=CodeRef(repo="repo", commit="def456", path="strategies/structure.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=30, threshold=Decimal("0.4")),
        cost=CostRef(spread=Decimal("0.15"), commission=Decimal("0.07")),
        config=ConfigRef(env="prod", region="us-west-2"),
    )
    registry.register_experiment(ref1)
    registry.register_experiment(ref2)
    results = registry.find_experiments_by_strategy("trend_follow", "v2")
    assert len(results) == 2


def test_find_experiments_by_parameter():
    """find_experiments_by_parameter returns experiments matching a parameter."""
    registry = ExperimentRegistry()
    ref1 = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    ref2 = ExperimentRef(
        experiment_id="exp_2",
        code=CodeRef(repo="repo", commit="def456", path="strategies/structure.py"),
        strategy=StrategyRef(name="structure_liq", version="v1"),
        parameters=ParameterRef(window=50, threshold=Decimal("0.3")),
        cost=CostRef(spread=Decimal("0.2"), commission=Decimal("0.1")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    registry.register_experiment(ref1)
    registry.register_experiment(ref2)
    results = registry.find_experiments_by_parameter(window=20)
    assert len(results) == 1
    assert results[0] == "exp_1"


def test_experiment_registry_deterministic():
    """Same inputs yield identical registry results."""
    r1 = ExperimentRegistry()
    r2 = ExperimentRegistry()
    ref = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    r1.register_experiment(ref)
    r2.register_experiment(ref)
    assert r1.get_experiment("exp_1") == r2.get_experiment("exp_1")


def test_code_ref_creates():
    """CodeRef can be created."""
    cr = CodeRef(repo="repo", commit="abc123", path="strategies/trend.py")
    assert cr.repo == "repo"
    assert cr.commit == "abc123"
    assert cr.path == "strategies/trend.py"


def test_strategy_ref_creates():
    """StrategyRef can be created."""
    sr = StrategyRef(name="trend_follow", version="v2")
    assert sr.name == "trend_follow"
    assert sr.version == "v2"


def test_parameter_ref_creates():
    """ParameterRef can be created."""
    pr = ParameterRef(window=20, threshold=Decimal("0.5"))
    assert pr.window == 20
    assert pr.threshold == Decimal("0.5")


def test_cost_ref_creates():
    """CostRef can be created."""
    cr = CostRef(spread=Decimal("0.1"), commission=Decimal("0.05"))
    assert cr.spread == Decimal("0.1")
    assert cr.commission == Decimal("0.05")


def test_config_ref_creates():
    """ConfigRef can be created."""
    cr = ConfigRef(env="prod", region="us-east-1")
    assert cr.env == "prod"
    assert cr.region == "us-east-1"


def test_experiment_ref_creates():
    """ExperimentRef can be created."""
    er = ExperimentRef(
        experiment_id="exp_1",
        code=CodeRef(repo="repo", commit="abc123", path="strategies/trend.py"),
        strategy=StrategyRef(name="trend_follow", version="v2"),
        parameters=ParameterRef(window=20, threshold=Decimal("0.5")),
        cost=CostRef(spread=Decimal("0.1"), commission=Decimal("0.05")),
        config=ConfigRef(env="prod", region="us-east-1"),
    )
    assert er.experiment_id == "exp_1"
