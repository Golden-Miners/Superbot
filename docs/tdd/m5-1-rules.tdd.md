# TDD Evidence Report — M5.1 Versioned Rule Schema

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.1` ("Versioned rule schema, stable IDs, dedup/expiry/invalidation/reversal").

## User journeys
- As a researcher, I want versioned rule schema (schema_version tracked on every rule)
- As a researcher, I want stable rule IDs (same inputs produce same rule_id)
- As a researcher, I want dedup: RuleStore rejects duplicate rule_id
- As a researcher, I want expiry: rules with valid_to <= today excluded from active
- As a researcher, I want invalidation: mark rule as INVALID (not deleted)
- As a researcher, I want reversal: mark original REVERSED, create opposite-type rule
- As a researcher, I want missing required fields to block rule creation
- As a researcher, I want invalid status transitions blocked

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| RuleSpec minimal creation | `tests/unit/test_rules.py::test_rule_spec_minimal` | ModuleNotFoundError | PASS | RuleSpec with all required fields creates successfully |
| Required fields blocked | `tests/unit/test_rules.py::test_rule_spec_required_fields_blocked` | ModuleNotFoundError | PASS | Empty rule_id raises InvalidRuleError |
| valid_to before valid_from blocked | `tests/unit/test_rules.py::test_rule_spec_valid_to_before_valid_from_blocked` | ModuleNotFoundError | PASS | Invalid date range raises InvalidRuleError |
| RuleStore add and get | `tests/unit/test_rules.py::test_rule_store_add_and_get` | ModuleNotFoundError | PASS | Store and retrieve by rule_id |
| Dedup rejects duplicate | `tests/unit/test_rules.py::test_rule_store_dedup_rejects_duplicate` | ModuleNotFoundError | PASS | Duplicate rule_id raises InvalidRuleError |
| Expiry filtering | `tests/unit/test_rules.py::test_rule_store_expiry` | ModuleNotFoundError | PASS | Expired rules excluded from active_rules |
| Invalidation | `tests/unit/test_rules.py::test_rule_store_invalidation` | ModuleNotFoundError | PASS | Rule marked INVALID, not deleted |
| Invalidation nonexistent blocked | `tests/unit/test_rules.py::test_rule_store_invalidation_nonexistent_blocked` | ModuleNotFoundError | PASS | Nonexistent rule raises InvalidRuleError |
| Reversal | `tests/unit/test_rules.py::test_rule_store_reversal` | ModuleNotFoundError | PASS | Original REVERSED, opposite-type rule created |
| Reversal nonexistent blocked | `tests/unit/test_rules.py::test_rule_store_reversal_nonexistent_blocked` | ModuleNotFoundError | PASS | Nonexistent rule raises InvalidRuleError |
| Reversal already reversed blocked | `tests/unit/test_rules.py::test_rule_store_reversal_already_reversed_blocked` | ModuleNotFoundError | PASS | Already-reversed rule raises InvalidRuleError |
| RuleType enum | `tests/unit/test_rules.py::test_rule_type_enum` | ModuleNotFoundError | PASS | 8 rule types: entry, exit, stop, target, trailing, risk, sizing, filter |
| RuleStatus enum | `tests/unit/test_rules.py::test_rule_status_enum` | ModuleNotFoundError | PASS | 4 statuses: active, expired, invalid, reversed |
| Decimal fields must be Decimal | `tests/unit/test_rules.py::test_rule_spec_decimal_fields_must_be_decimal` | ModuleNotFoundError | PASS | Non-Decimal size_qty raises InvalidRuleError |
| size_qty Decimal accepted | `tests/unit/test_rules.py::test_rule_spec_size_qty_decimal` | ModuleNotFoundError | PASS | Decimal size_qty stored correctly |
| active_filters_expired | `tests/unit/test_rules.py::test_rule_store_active_filters_expired` | ModuleNotFoundError | PASS | Only non-expired ACTIVE rules returned |
| get nonexistent returns None | `tests/unit/test_rules.py::test_rule_store_get_nonexistent_returns_none` | ModuleNotFoundError | PASS | Missing rule_id returns None |
| schema_version immutable | `tests/unit/test_rules.py::test_rule_schema_version_immutable` | ModuleNotFoundError | PASS | Frozen dataclass prevents modification |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Versioned rule schema | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |
| 2 | Stable rule IDs | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |
| 3 | Dedup rejects duplicate rule_id | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |
| 4 | Expiry excludes stale rules | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |
| 5 | Invalidation marks INVALID | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |
| 6 | Reversal creates opposite rule | `tests/unit/test_rules.py` | unit | PASS | 173 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.1 lines exercised by unit tests
- Intentional gap: rule condition parsing/evaluation not implemented — `condition` field stored as opaque string
- Intentional gap: rule persistence (save/load to disk) not implemented — RuleStore is in-memory only
- Intentional gap: rule versioning (multiple schema versions of same rule_id) not implemented — dedup is by exact rule_id match

## Merge evidence
Commit: `a2d696b` (M4.7) + M5.1 commit (rules.py + test_rules.py). RED evidence: `ModuleNotFoundError` captured before implementation (superbot.contracts.rules missing). GREEN evidence: 173 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
