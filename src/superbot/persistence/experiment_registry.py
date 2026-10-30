"""Experiment registry: data-code-strategy-parameter-cost-config refs (schema.md section 8.4).

Deterministic experiment registry service:
- Register experiments linking code, strategy, parameters, cost, and config refs
- Lookup experiment by id
- Lookup all experiments by code commit, strategy name+version, or parameter
- Missing refs return None rather than crashing
- Stdlib-only; no import-time network/DB activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CodeRef:
    """Reference to code used by an experiment."""

    repo: str
    commit: str
    path: str


@dataclass(frozen=True)
class StrategyRef:
    """Reference to a strategy used by an experiment."""

    name: str
    version: str


@dataclass(frozen=True)
class ParameterRef:
    """Reference to strategy parameters used by an experiment."""

    window: int
    threshold: Any


@dataclass(frozen=True)
class CostRef:
    """Reference to cost assumptions used by an experiment."""

    spread: Any
    commission: Any


@dataclass(frozen=True)
class ConfigRef:
    """Reference to environment config used by an experiment."""

    env: str
    region: str


@dataclass(frozen=True)
class ExperimentRef:
    """Complete reference set for an experiment: code, strategy, parameters, cost, config."""

    experiment_id: str
    code: CodeRef
    strategy: StrategyRef
    parameters: ParameterRef
    cost: CostRef
    config: ConfigRef


class ExperimentRegistry:
    """Registry linking experiments to code, strategy, parameters, cost, config refs."""

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentRef] = {}
        self._by_code: dict[str, list[str]] = {}
        self._by_strategy: dict[tuple[str, str], list[str]] = {}
        self._by_parameter_window: dict[int, list[str]] = {}

    def register_experiment(self, ref: ExperimentRef) -> None:
        """Register an experiment with all its refs."""
        self._experiments[ref.experiment_id] = ref
        self._by_code.setdefault(ref.code.commit, []).append(ref.experiment_id)
        self._by_strategy.setdefault((ref.strategy.name, ref.strategy.version), []).append(
            ref.experiment_id
        )
        self._by_parameter_window.setdefault(ref.parameters.window, []).append(ref.experiment_id)

    def get_experiment(self, experiment_id: str) -> ExperimentRef | None:
        """Get an experiment ref by id."""
        return self._experiments.get(experiment_id)

    def find_experiments_by_code(self, commit: str) -> list[str]:
        """Find experiment ids using a given code commit."""
        return list(self._by_code.get(commit, []))

    def find_experiments_by_strategy(self, name: str, version: str) -> list[str]:
        """Find experiment ids using a given strategy name+version."""
        return list(self._by_strategy.get((name, version), []))

    def find_experiments_by_parameter(self, window: int) -> list[str]:
        """Find experiment ids using a given parameter window."""
        return list(self._by_parameter_window.get(window, []))


def register_experiment(
    registry: ExperimentRegistry,
    experiment_id: str,
    code: CodeRef,
    strategy: StrategyRef,
    parameters: ParameterRef,
    cost: CostRef,
    config: ConfigRef,
) -> None:
    """Register an experiment (convenience function)."""
    registry.register_experiment(
        ExperimentRef(
            experiment_id=experiment_id,
            code=code,
            strategy=strategy,
            parameters=parameters,
            cost=cost,
            config=config,
        )
    )


def get_experiment_refs(registry: ExperimentRegistry, experiment_id: str) -> ExperimentRef | None:
    """Get experiment refs by id (convenience function)."""
    return registry.get_experiment(experiment_id)


def find_experiments_by_code(registry: ExperimentRegistry, commit: str) -> list[str]:
    """Find experiment ids by code commit (convenience function)."""
    return registry.find_experiments_by_code(commit)


def find_experiments_by_strategy(
    registry: ExperimentRegistry, name: str, version: str
) -> list[str]:
    """Find experiment ids by strategy name+version (convenience function)."""
    return registry.find_experiments_by_strategy(name, version)


def find_experiments_by_parameter(registry: ExperimentRegistry, window: int) -> list[str]:
    """Find experiment ids by parameter window (convenience function)."""
    return registry.find_experiments_by_parameter(window)


# ArtifactRef is an alias for ExperimentRef, kept for API compatibility.
ArtifactRef = ExperimentRef
