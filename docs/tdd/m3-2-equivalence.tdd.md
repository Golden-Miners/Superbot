# TDD Evidence Report — M3.2 Equivalence fixtures, strategy rules, cost conventions, acceptance tests

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.2` ("Define equivalence fixtures, strategy rules, cost conventions and acceptance tests before candidate tests") and `M3.2a` ("Freeze the standardized POC protocol").

## User journeys
- As a researcher, I want standardized equivalence fixtures so NautilusTrader, LEAN, and the custom baseline all run identical inputs/rules/costs/splits.
- As a researcher, I want strategy rules defined in a machine-testable form so engine comparisons are apples-to-apples.
- As a researcher, I want cost conventions (spread/slippage/commission/swap/funding) defined and applied consistently across engines.
- As a researcher, I want acceptance tests (correctness gates) defined before candidate tests run, so engines pass/fail deterministically.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Equivalence fixture has known bars | `tests/unit/test_equivalence.py::test_equivalence_fixture_has_known_bars` | ModuleNotFoundError | PASS | 10-bar canonical fixture, ts 1–10 |
| Cost convention defaults | `test_cost_convention_defaults` | ModuleNotFoundError | PASS | Zero-cost default convention |
| Cost convention applies to trade | `test_cost_convention_applies_to_trade` | ModuleNotFoundError | PASS | spread + 2×slippage + 2×commission + swap |
| Strategy rule machine-testable fields | `test_strategy_rule_machine_testable_fields` | ModuleNotFoundError | PASS | name/family/conditions/parameters explicit |
| Acceptance passes for baseline | `test_run_acceptance_passes_for_baseline` | ModuleNotFoundError | PASS | correctness gate passed, events > 0 |
| Unknown engine raises | `test_run_acceptance_unknown_engine_raises` | ModuleNotFoundError | PASS | `UnknownStrategyRuleError` raised |

## Test specification
| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Canonical 10-bar equivalence fixture shared across engines | `tests/unit/test_equivalence.py` | unit | PASS | 174-test suite, TEST_EXIT:True |
| 2 | Cost convention totals spread+slippage+commission+swap funding | `tests/unit/test_equivalence.py` | unit | PASS | 174-test suite |
| 3 | StrategyRule fields explicit and versioned (no discretionary prose) | `tests/unit/test_equivalence.py` | unit | PASS | 174-test suite |
| 4 | Acceptance run returns correctness gate + event count + reasons | `tests/unit/test_equivalence.py` | unit | PASS | 174-test suite |
| 5 | Unknown engine raises `UnknownStrategyRuleError` | `tests/unit/test_equivalence.py` | unit | PASS | 174-test suite |

## Coverage and known gaps
- No coverage tool configured; all M3.2 lines exercised by unit tests.
- Intentional gap: only `custom_baseline` engine has an acceptance implementation; NautilusTrader and LEAN adapters are registered as known engines only when POCs run (M3.3/M3.4).
- Intentional gap: strategy rules are defined but not yet executed against market data — execution belongs to M3.3/M3.4 engine POCs.
- Semantics preserved exactly from `superbot_poc.py` so candidate engines have a stable, comparable reference.

## Merge evidence
Commit: `be3f1a8` (M3.2 implementation + tests). RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 174 tests pass, ruff clean, format clean, `git diff --check` clean, working tree clean.
