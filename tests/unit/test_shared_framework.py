"""RED tests for M5.5 — Shared framework and versioned configs; no ten LLM strategy agents.

Tests define:
- SharedStrategyFramework: a single shared framework for all strategy rules
- Versioned strategy configs: schema_version, config_id, rule_refs, parameters
- Framework registration: register strategy configs by rule_id
- Dedup: reject duplicate config_id
- Single framework instance: all strategies use the same framework (no ten LLM agents)
- Config retrieval: get config by rule_id
- Config validation: required fields present, rule_refs reference valid rules
- Versioned configs: new schema_version doesn't break old configs
- No discretionary terms: all parameters explicit numeric values
- Deterministic: same inputs produce identical config lookup
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.strategy.shared_framework import (
    SharedStrategyFramework,
    StrategyConfig,
    StrategyConfigError,
)


def _fw() -> SharedStrategyFramework:
    """Get a fresh framework instance (resets singleton state)."""
    SharedStrategyFramework.reset()
    return SharedStrategyFramework()


def test_shared_framework_singleton():
    """Only one framework instance exists (no ten LLM strategy agents)."""
    f1 = SharedStrategyFramework()
    f2 = SharedStrategyFramework()
    assert f1 is f2


def test_shared_framework_register_and_get():
    """Register a strategy config and retrieve it by rule_id."""
    fw = _fw()
    cfg = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_trend_001",
        rule_refs=["rule_entry_trend", "rule_exit_target"],
        parameters={"lookback_bars": 20, "ma_period": 5, "stop_pct": Decimal("2.0")},
    )
    fw.register(cfg)
    retrieved = fw.get("cfg_trend_001")
    assert retrieved is cfg
    assert retrieved.config_id == "cfg_trend_001"


def test_shared_framework_dedup_rejects_duplicate():
    """Registering duplicate config_id raises StrategyConfigError."""
    fw = _fw()
    cfg = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_dup_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(1)},
    )
    fw.register(cfg)
    with pytest.raises(StrategyConfigError):
        fw.register(cfg)


def test_shared_framework_get_nonexistent_returns_none():
    """get() returns None for nonexistent config_id."""
    fw = _fw()
    assert fw.get("cfg_nope") is None


def test_shared_framework_validates_rule_refs():
    """Config with empty rule_refs raises StrategyConfigError."""
    with pytest.raises(StrategyConfigError):
        StrategyConfig(
            schema_version="1.0.0",
            config_id="cfg_empty_refs",
            rule_refs=[],
            parameters={},
        )


def test_shared_framework_versioned_configs():
    """Different schema_versions can coexist under different config_ids."""
    fw = _fw()
    cfg_v1 = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_v1_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(1)},
    )
    cfg_v2 = StrategyConfig(
        schema_version="2.0.0",
        config_id="cfg_v2_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(2), "y": Decimal(3)},
    )
    fw.register(cfg_v1)
    fw.register(cfg_v2)
    assert fw.get("cfg_v1_001").schema_version == "1.0.0"
    assert fw.get("cfg_v2_001").schema_version == "2.0.0"


def test_shared_framework_no_ten_llm_agents():
    """Framework is a singleton — no separate LLM agent per strategy."""
    fw1 = SharedStrategyFramework()
    fw2 = SharedStrategyFramework()
    cfg = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_single_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(1)},
    )
    fw1.register(cfg)
    # The same framework instance (fw2) should see the registration
    assert fw2.get("cfg_single_001") is cfg


def test_shared_framework_all_configs():
    """all_configs() returns all registered configs."""
    fw = _fw()
    c1 = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_a_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(1)},
    )
    c2 = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_b_001",
        rule_refs=["rule_b"],
        parameters={"y": Decimal(2)},
    )
    fw.register(c1)
    fw.register(c2)
    all_cfg = fw.all_configs()
    assert len(all_cfg) == 2
    ids = {c.config_id for c in all_cfg}
    assert ids == {"cfg_a_001", "cfg_b_001"}


def test_shared_framework_deterministic():
    """Same registration produces identical config lookup."""
    fw = _fw()
    cfg = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_det_001",
        rule_refs=["rule_a"],
        parameters={"x": Decimal(1), "y": Decimal(2)},
    )
    fw.register(cfg)
    r1 = fw.get("cfg_det_001")
    r2 = fw.get("cfg_det_001")
    assert r1 is r2


def test_shared_framework_parameters_explicit():
    """All parameters are explicit numeric values (no discretionary terms)."""
    cfg = StrategyConfig(
        schema_version="1.0.0",
        config_id="cfg_explicit_001",
        rule_refs=["rule_a"],
        parameters={
            "lookback_bars": 20,
            "ma_period": 5,
            "stop_pct": Decimal("2.0"),
            "target_pct": Decimal("4.0"),
        },
    )
    assert cfg.parameters["lookback_bars"] == 20
    assert cfg.parameters["ma_period"] == 5
    assert cfg.parameters["stop_pct"] == Decimal("2.0")
    assert cfg.parameters["target_pct"] == Decimal("4.0")


def test_shared_framework_config_id_required():
    """Empty config_id raises StrategyConfigError."""
    with pytest.raises(StrategyConfigError):
        StrategyConfig(
            schema_version="1.0.0",
            config_id="",
            rule_refs=["rule_a"],
            parameters={},
        )


def test_shared_framework_schema_version_required():
    """Empty schema_version raises StrategyConfigError."""
    with pytest.raises(StrategyConfigError):
        StrategyConfig(
            schema_version="",
            config_id="cfg_schema_001",
            rule_refs=["rule_a"],
            parameters={},
        )
