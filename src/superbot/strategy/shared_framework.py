"""Shared strategy framework (schema.md section 5.5).

A single shared framework for all strategy rules — versioned configs identified
by stable config_id, with dedup, validation, and singleton enforcement so that
no ten LLM strategy agents proliferate. All parameters are explicit numeric
values; no discretionary terms.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self


class StrategyConfigError(ValueError):
    """Raised when a strategy config fails validation or a store operation
    cannot be completed."""


@dataclass(frozen=True)
class StrategyConfig:
    """Versioned strategy configuration.

    All parameter values are explicit numerics (int or Decimal); no
    discretionary or LLM-generated terms.
    """

    schema_version: str
    config_id: str
    rule_refs: list[str]
    parameters: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_refs", list(self.rule_refs))
        object.__setattr__(self, "parameters", dict(self.parameters))
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise StrategyConfigError("schema_version is required")
        if not isinstance(self.config_id, str) or not self.config_id:
            raise StrategyConfigError("config_id is required")
        if not isinstance(self.rule_refs, list) or len(self.rule_refs) == 0:
            raise StrategyConfigError("rule_refs must be a non-empty list")
        if not all(isinstance(r, str) and r for r in self.rule_refs):
            raise StrategyConfigError("rule_refs entries must be non-empty strings")
        if not isinstance(self.parameters, dict):
            raise StrategyConfigError("parameters must be a dict")
        for k, v in self.parameters.items():
            if not isinstance(k, str) or not k:
                raise StrategyConfigError("parameter keys must be non-empty strings")
            if not isinstance(v, (int, float, Decimal)) and not isinstance(v, str):
                raise StrategyConfigError(f"parameter '{k}' value must be a numeric or string")


class SharedStrategyFramework:
    """Singleton framework managing all strategy configs.

    Ensures one shared framework instance — no ten LLM strategy agents.
    """

    _instance: SharedStrategyFramework | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configs: dict[str, StrategyConfig] = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear all registered configs (test helper)."""
        if cls._instance is not None:
            cls._instance._configs.clear()

    def register(self, config: StrategyConfig) -> None:
        """Register a strategy config; reject duplicate config_id."""
        if config.config_id in self._configs:
            raise StrategyConfigError(f"config_id already exists: {config.config_id}")
        self._configs[config.config_id] = config

    def get(self, config_id: str) -> StrategyConfig | None:
        """Retrieve a strategy config by config_id; returns None if not found."""
        return self._configs.get(config_id)

    def all_configs(self) -> list[StrategyConfig]:
        """Return all registered strategy configs."""
        return list(self._configs.values())
