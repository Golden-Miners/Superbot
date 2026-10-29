"""RED tests for M5.1 — Versioned rule schema, stable IDs, dedup/expiry/invalidation/reversal.

Tests define:
- RuleSpec with schema_version, rule_id, rule_type, status, valid_from, valid_to
- Stable IDs: same inputs produce same rule_id
- Versioned schema: schema_version tracked on every rule
- Dedup: RuleStore rejects duplicate rule_ids
- Expiry: rules with valid_to <= now are expired
- Invalidation: mark rule as invalid (not deleted)
- Reversal: create reversed rule that cancels original
- Rule activation/deactivation
- Missing required fields block rule creation
- Invalid status transitions blocked
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from superbot.contracts.rules import (
    InvalidRuleError,
    RuleSpec,
    RuleStatus,
    RuleStore,
    RuleType,
)


def test_rule_spec_minimal():
    """RuleSpec with all required fields creates successfully."""
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_entry_trend_001",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
        condition="close > sma(20)",
    )
    assert rule.schema_version == "1.0.0"
    assert rule.rule_id == "rule_entry_trend_001"
    assert rule.rule_type == RuleType.ENTRY
    assert rule.status == RuleStatus.ACTIVE
    assert rule.symbol == "ESZ25"


def test_rule_spec_required_fields_blocked():
    """Missing required fields block rule creation."""
    with pytest.raises(InvalidRuleError):
        RuleSpec(
            schema_version="1.0.0",
            rule_id="",
            rule_type=RuleType.ENTRY,
            status=RuleStatus.ACTIVE,
            valid_from=date.today(),
        )


def test_rule_spec_valid_to_before_valid_from_blocked():
    """valid_to before valid_from blocks rule creation."""
    with pytest.raises(InvalidRuleError):
        RuleSpec(
            schema_version="1.0.0",
            rule_id="rule_bad_001",
            rule_type=RuleType.ENTRY,
            status=RuleStatus.ACTIVE,
            valid_from=date.today() + timedelta(days=10),
            valid_to=date.today(),
        )


def test_rule_store_add_and_get():
    """RuleStore stores and retrieves rules by rule_id."""
    store = RuleStore()
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_001",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    store.add(rule)
    assert store.get("rule_001") is rule


def test_rule_store_dedup_rejects_duplicate():
    """RuleStore rejects duplicate rule_id."""
    store = RuleStore()
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_001",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    store.add(rule)
    with pytest.raises(InvalidRuleError):
        store.add(rule)


def test_rule_store_expiry():
    """RuleStore marks rules as expired when valid_to <= today."""
    store = RuleStore()
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_expired",
        rule_type=RuleType.EXIT,
        status=RuleStatus.ACTIVE,
        valid_from=date.today() - timedelta(days=30),
        valid_to=date.today() - timedelta(days=1),
        symbol="ESZ25",
    )
    store.add(rule)
    active = store.active_rules()
    assert "rule_expired" not in [r.rule_id for r in active]


def test_rule_store_invalidation():
    """RuleStore can invalidate a rule (not delete)."""
    store = RuleStore()
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_invalid",
        rule_type=RuleType.STOP,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    store.add(rule)
    store.invalidate("rule_invalid")
    retrieved = store.get("rule_invalid")
    assert retrieved.status == RuleStatus.INVALID


def test_rule_store_invalidation_nonexistent_blocked():
    """Invalidating a nonexistent rule raises InvalidRuleError."""
    store = RuleStore()
    with pytest.raises(InvalidRuleError):
        store.invalidate("rule_does_not_exist")


def test_rule_store_reversal():
    """RuleStore can reverse a rule, creating a reversed rule that cancels original."""
    store = RuleStore()
    original = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_reverse_me",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    store.add(original)
    reversed_rule = store.reverse("rule_reverse_me", "rule_reversal_of_001")
    assert reversed_rule.rule_type == RuleType.EXIT  # entry reversed -> exit
    assert reversed_rule.status == RuleStatus.ACTIVE
    assert store.get("rule_reverse_me").status == RuleStatus.REVERSED


def test_rule_store_reversal_nonexistent_blocked():
    """Reversing a nonexistent rule raises InvalidRuleError."""
    store = RuleStore()
    with pytest.raises(InvalidRuleError):
        store.reverse("rule_does_not_exist", "rule_reversal_001")


def test_rule_store_reversal_already_reversed_blocked():
    """Reversing an already-reversed rule raises InvalidRuleError."""
    store = RuleStore()
    original = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_rev2",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    store.add(original)
    store.reverse("rule_rev2", "rule_rev2_rev1")
    with pytest.raises(InvalidRuleError):
        store.reverse("rule_rev2", "rule_rev2_rev2")


def test_rule_type_enum():
    """RuleType enum has expected values."""
    assert RuleType.ENTRY == "entry"
    assert RuleType.EXIT == "exit"
    assert RuleType.STOP == "stop"
    assert RuleType.TARGET == "target"
    assert RuleType.TRAILING == "trailing"
    assert RuleType.RISK == "risk"
    assert RuleType.SIZING == "sizing"
    assert RuleType.FILTER == "filter"


def test_rule_status_enum():
    """RuleStatus enum has expected values."""
    assert RuleStatus.ACTIVE == "active"
    assert RuleStatus.EXPIRED == "expired"
    assert RuleStatus.INVALID == "invalid"
    assert RuleStatus.REVERSED == "reversed"


def test_rule_spec_decimal_fields_must_be_decimal():
    """Decimal fields must be Decimal or null."""
    with pytest.raises(InvalidRuleError):
        RuleSpec(
            schema_version="1.0.0",
            rule_id="rule_bad_decimal",
            rule_type=RuleType.SIZING,
            status=RuleStatus.ACTIVE,
            valid_from=date.today(),
            symbol="ESZ25",
            size_qty="not_a_decimal",
        )


def test_rule_spec_size_qty_decimal():
    """size_qty accepts Decimal values."""
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_size",
        rule_type=RuleType.SIZING,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
        size_qty=Decimal("1.5"),
    )
    assert rule.size_qty == Decimal("1.5")


def test_rule_store_active_filters_expired():
    """active_rules() excludes expired and invalid rules."""
    store = RuleStore()
    active_rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_active",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    expired_rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_exp",
        rule_type=RuleType.EXIT,
        status=RuleStatus.ACTIVE,
        valid_from=date.today() - timedelta(days=30),
        valid_to=date.today() - timedelta(days=1),
        symbol="ESZ25",
    )
    store.add(active_rule)
    store.add(expired_rule)
    active = store.active_rules()
    assert len(active) == 1
    assert active[0].rule_id == "rule_active"


def test_rule_store_get_nonexistent_returns_none():
    """get() returns None for nonexistent rule_id."""
    store = RuleStore()
    assert store.get("rule_nope") is None


def test_rule_schema_version_immutable():
    """schema_version cannot be changed after creation (frozen dataclass)."""
    rule = RuleSpec(
        schema_version="1.0.0",
        rule_id="rule_ver",
        rule_type=RuleType.ENTRY,
        status=RuleStatus.ACTIVE,
        valid_from=date.today(),
        symbol="ESZ25",
    )
    with pytest.raises(AttributeError):
        rule.schema_version = "2.0.0"
