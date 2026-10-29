# TDD Evidence Report — M7.4 Tier Multipliers, Monthly Review, Max 10% Relative Increase

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.4` ("Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase; numeric tier criteria remain OPEN").

## User journeys
- As a risk manager, I want tier multipliers restricted to {0.25, 0.50, 0.75, 1.00}
- As a risk manager, I want default multiplier 1.00 for unknown strategies
- As a risk manager, I want monthly review cadence with last/next review dates
- As a risk manager, I want max 10% relative increase per review (snaps down to nearest valid tier)
- As a risk manager, I want decreases always allowed
- As a risk manager, I want numeric tier criteria to remain OPEN (no auto-assignment)
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| TierMultiplier creation | `tests/unit/test_tier_multiplier.py::test_tier_multiplier_creates` | ModuleNotFoundError | PASS | Multiplier value stored |
| Valid tier values | `tests/unit/test_tier_multiplier.py::test_tier_multiplier_valid_values` | ModuleNotFoundError | PASS | Only 0.25/0.50/0.75/1.00 accepted |
| Service creation | `tests/unit/test_tier_multiplier.py::test_tier_multiplier_service_creates` | ModuleNotFoundError | PASS | Service instantiates |
| Default multiplier | `tests/unit/test_tier_multiplier.py::test_get_tier_multiplier_default` | ModuleNotFoundError | PASS | Unknown strategy → 1.00 |
| Assign tier | `tests/unit/test_tier_multiplier.py::test_assign_tier_multiplier` | ModuleNotFoundError | PASS | Multiplier set and retrievable |
| Invalid tier rejected | `tests/unit/test_tier_multiplier.py::test_assign_tier_multiplier_invalid_value` | ModuleNotFoundError | PASS | 0.30 raises ValueError |
| Monthly review cadence | `tests/unit/test_tier_multiplier.py::test_review_tier_monthly_cadence` | ModuleNotFoundError | PASS | Next review ~30 days after last |
| 10% cap blocks increase | `tests/unit/test_tier_multiplier.py::test_max_10_percent_relative_increase_blocked` | ModuleNotFoundError | PASS | 0.50→0.75 capped to 0.50 |
| Decrease allowed | `tests/unit/test_tier_multiplier.py::test_decrease_always_allowed` | ModuleNotFoundError | PASS | 1.00→0.50 allowed |
| Tier criteria OPEN | `tests/unit/test_tier_multiplier.py::test_tier_criteria_remain_open` | ModuleNotFoundError | PASS | No auto-assignment; default 1.00 |
| Deterministic | `tests/unit/test_tier_multiplier.py::test_tier_multiplier_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| TierMultiplierResult | `tests/unit/test_tier_multiplier.py::test_tier_multiplier_result_creates` | ModuleNotFoundError | PASS | Result dataclass with all fields |
| Next review None | `tests/unit/test_tier_multiplier.py::test_next_review_date_none_when_unreviewed` | ModuleNotFoundError | PASS | Unreviewed → None |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Fixed tier values {0.25,0.50,0.75,1.00} | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |
| 2 | Monthly review cadence | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |
| 3 | 10% relative increase cap | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |
| 4 | Decreases always allowed | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |
| 5 | Tier criteria OPEN | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_tier_multiplier.py` | unit | PASS | 413 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.4 lines exercised by unit tests
- Intentional gap: No persistence of tier assignments — in-memory only
- Intentional gap: Numeric tier criteria remain OPEN (not auto-assigned); caller must supply criteria
- Intentional gap: review date uses date.today(); not injectable for deterministic date testing

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.tier_multiplier'` captured before implementation. GREEN: 413 tests pass, 2 skipped, ruff clean, format clean, working tree clean.