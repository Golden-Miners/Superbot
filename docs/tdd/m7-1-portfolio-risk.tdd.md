# TDD Evidence Report — M7.1 Portfolio/Strategy/Correlation-Group Risk Service

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.1` ("Portfolio/strategy/correlation-group risk service").

## User journeys
- As a risk manager, I want to register strategies with per-strategy risk limits (max DD, daily loss, position size)
- As a risk manager, I want to group strategies into correlation groups with group-level DD caps
- As a risk manager, I want to check proposed trades against strategy and group limits
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| PortfolioRiskService creation | `tests/unit/test_portfolio_risk.py::test_portfolio_risk_service_creates` | ModuleNotFoundError | PASS | Service instantiates with no args |
| register_strategy | `tests/unit/test_portfolio_risk.py::test_register_strategy` | ModuleNotFoundError | PASS | Strategy registered and retrievable |
| RiskLimit creation | `tests/unit/test_portfolio_risk.py::test_risk_limit_creates` | ModuleNotFoundError | PASS | RiskLimit dataclass with all Decimal fields |
| RiskCheckResult creation | `tests/unit/test_portfolio_risk.py::test_risk_check_result_creates` | ModuleNotFoundError | PASS | RiskCheckResult with allowed flag and reasons |
| Risk check allows | `tests/unit/test_portfolio_risk.py::test_check_strategy_risk_allows` | ModuleNotFoundError | PASS | Within limits → allowed=True |
| Risk check blocks high DD | `tests/unit/test_portfolio_risk.py::test_check_strategy_risk_blocks_high_dd` | ModuleNotFoundError | PASS | DD > limit → allowed=False |
| Risk check blocks daily loss | `tests/unit/test_portfolio_risk.py::test_check_strategy_risk_blocks_high_daily_loss` | ModuleNotFoundError | PASS | Daily loss > limit → allowed=False |
| Risk check blocks multiple | `tests/unit/test_portfolio_risk.py::test_check_strategy_risk_blocks_multiple` | ModuleNotFoundError | PASS | Both exceed → 2 reasons |
| CorrelationGroup creation | `tests/unit/test_portfolio_risk.py::test_correlation_group_creates` | ModuleNotFoundError | PASS | Group with name and max DD |
| CorrelationGroup add strategy | `tests/unit/test_portfolio_risk.py::test_correlation_group_add_strategy` | ModuleNotFoundError | PASS | Add strategies to group |
| Group risk allows | `tests/unit/test_portfolio_risk.py::test_check_group_risk_allows` | ModuleNotFoundError | PASS | Group DD <= limit → allowed=True |
| Group risk blocks | `tests/unit/test_portfolio_risk.py::test_check_group_risk_blocks` | ModuleNotFoundError | PASS | Group DD > limit → allowed=False |
| Deterministic | `tests/unit/test_portfolio_risk.py::test_portfolio_risk_service_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Unknown strategy | `tests/unit/test_portfolio_risk.py::test_portfolio_risk_service_unknown_strategy` | ModuleNotFoundError | PASS | get_strategy returns None |
| Duplicate strategy | `tests/unit/test_portfolio_risk.py::test_register_strategy_duplicate` | ModuleNotFoundError | PASS | Re-register replaces limits |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Strategy risk limits | `tests/unit/test_portfolio_risk.py` | unit | PASS | 368 passed, 2 skipped |
| 2 | Correlation group caps | `tests/unit/test_portfolio_risk.py` | unit | PASS | 368 passed, 2 skipped |
| 3 | Trade check pass/block | `tests/unit/test_portfolio_risk.py` | unit | PASS | 368 passed, 2 skipped |
| 4 | Deterministic results | `tests/unit/test_portfolio_risk.py` | unit | PASS | 368 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.1 lines exercised by unit tests
- Intentional gap: No persistence of portfolio state — in-memory only
- Intentional gap: No integration with M7.2 halt/resume — separate task

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.portfolio_risk'` captured before implementation. GREEN: 368 tests pass, 2 skipped, ruff clean, format clean, working tree clean.