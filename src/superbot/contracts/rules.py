"""Versioned rule schema contract (schema.md section 5).

Rule specifications are versioned, identified by stable rule_id, and support
dedup/expiry/invalidation/reversal through RuleStore. Missing/stale fields
required for execution must block that operation at the call site; this module
preserves nulls and never substitutes typical values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class RuleType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    STOP = "stop"
    TARGET = "target"
    TRAILING = "trailing"
    RISK = "risk"
    SIZING = "sizing"
    FILTER = "filter"


class RuleStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVERSED = "reversed"


class InvalidRuleError(ValueError):
    """Raised when a rule specification fails validation or a store
    operation cannot be completed."""


# Decimal fields that must remain null-or-decimal (never coerced to zero).
_DECIMAL_FIELDS = ("size_qty", "price_limit", "stop_price", "target_price")


@dataclass(frozen=True)
class RuleSpec:
    """Versioned, immutable rule specification.

    rule_id is a stable identifier; schema_version tracks the schema version.
    """

    schema_version: str
    rule_id: str
    rule_type: RuleType
    status: RuleStatus
    valid_from: date
    symbol: str = ""
    valid_to: date | None = None
    condition: str = ""
    size_qty: Decimal | None = None
    price_limit: Decimal | None = None
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    source_metadata_ref: str = ""

    def __post_init__(self) -> None:
        self._validate_required()
        self._validate_decimals()
        self._validate_enums()
        self._validate_date_range()

    def _validate_required(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise InvalidRuleError("schema_version is required")
        if not isinstance(self.rule_id, str) or not self.rule_id:
            raise InvalidRuleError("rule_id is required")
        if not isinstance(self.symbol, str) or not self.symbol:
            raise InvalidRuleError("symbol is required")

    def _validate_decimals(self) -> None:
        for name in _DECIMAL_FIELDS:
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, Decimal):
                raise InvalidRuleError(f"{name} must be Decimal or null, got {value!r}")

    def _validate_enums(self) -> None:
        if not isinstance(self.rule_type, RuleType):
            raise InvalidRuleError(f"rule_type must be one of {[t.value for t in RuleType]}")
        if not isinstance(self.status, RuleStatus):
            raise InvalidRuleError(f"status must be one of {[s.value for s in RuleStatus]}")

    def _validate_date_range(self) -> None:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise InvalidRuleError(
                f"valid_to {self.valid_to} precedes valid_from {self.valid_from}"
            )


@dataclass
class RuleStore:
    """Manages rule lifecycle: add, get, dedup, expiry, invalidation, reversal."""

    def __init__(self) -> None:
        self._rules: dict[str, RuleSpec] = {}

    def add(self, rule: RuleSpec) -> None:
        """Add a rule; reject duplicate rule_id."""
        if rule.rule_id in self._rules:
            raise InvalidRuleError(f"rule_id already exists: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> RuleSpec | None:
        """Retrieve a rule by rule_id; returns None if not found."""
        return self._rules.get(rule_id)

    def active_rules(self) -> list[RuleSpec]:
        """Return rules that are ACTIVE and not expired (valid_to > today)."""
        today = date.today()
        return [
            rule
            for rule in self._rules.values()
            if rule.status == RuleStatus.ACTIVE and (rule.valid_to is None or rule.valid_to > today)
        ]

    def invalidate(self, rule_id: str) -> None:
        """Mark a rule as INVALID (not deleted)."""
        rule = self._rules.get(rule_id)
        if rule is None:
            raise InvalidRuleError(f"rule_id not found: {rule_id}")
        if rule.status != RuleStatus.ACTIVE:
            raise InvalidRuleError(
                f"cannot invalidate rule {rule_id} with status {rule.status.value}"
            )
        object.__setattr__(rule, "status", RuleStatus.INVALID)

    def reverse(self, rule_id: str, reversed_rule_id: str) -> RuleSpec:
        """Reverse a rule: mark original REVERSED, create a new rule of the
        opposite type with the given reversed_rule_id."""
        original = self._rules.get(rule_id)
        if original is None:
            raise InvalidRuleError(f"rule_id not found: {rule_id}")
        if original.status != RuleStatus.ACTIVE:
            raise InvalidRuleError(
                f"cannot reverse rule {rule_id} with status {original.status.value}"
            )
        object.__setattr__(original, "status", RuleStatus.REVERSED)

        reversed_type = RuleType.EXIT if original.rule_type == RuleType.ENTRY else RuleType.ENTRY
        reversed_rule = RuleSpec(
            schema_version=original.schema_version,
            rule_id=reversed_rule_id,
            rule_type=reversed_type,
            status=RuleStatus.ACTIVE,
            valid_from=original.valid_from,
            valid_to=original.valid_to,
            symbol=original.symbol,
            condition=original.condition,
            size_qty=original.size_qty,
            price_limit=original.price_limit,
            stop_price=original.stop_price,
            target_price=original.target_price,
            source_metadata_ref=original.source_metadata_ref,
        )
        self.add(reversed_rule)
        return reversed_rule
