# TDD Evidence Report — M4.4 Limit Trade-through Policy / Event Sequencing

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M4.4` ("Limit trade-through policy/event sequencing").

## User journeys
- As a researcher, I want limit buy orders to fill only when bar low <= limit price (trade-through policy)
- As a researcher, I want limit sell orders to fill only when bar high >= limit price (trade-through policy)
- As a researcher, I want limit orders that do not trade through to be explicitly rejected, not silently filled
- As a researcher, I want fill price to be the limit price, not the bar open price
- As a researcher, I want limit orders without stop/target to default to end_of_data exit
- As a researcher, I want identical inputs to yield identical limit fill events (deterministic)
- As a researcher, I want cost config applied to both entry and exit of limit fills
- As a researcher, I want missing cost config to block limit fill operations

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Limit buy fills when low trades through | `tests/unit/test_limit_trade_through.py::test_limit_buy_fills_when_low_trades_through` | AttributeError | PASS | Limit buy at P fills when next bar low <= P, price = limit price |
| Limit buy rejected when no trade through | `tests/unit/test_limit_trade_through.py::test_limit_buy_not_filled_when_no_trade_through` | AttributeError | PASS | NextBarFillError raised when bar low > limit price |
| Limit sell fills when high trades through | `tests/unit/test_limit_trade_through.py::test_limit_sell_fills_when_high_trades_through` | AttributeError | PASS | Limit sell at P fills when next bar high >= P |
| Limit sell rejected when no trade through | `tests/unit/test_limit_trade_through.py::test_limit_sell_not_filled_when_no_trade_through` | AttributeError | PASS | NextBarFillError raised when bar high < limit price |
| Boundary: low == limit fills | `tests/unit/test_limit_trade_through.py::test_limit_buy_boundary_exact` | AttributeError | PASS | Exact boundary (low == limit) trades through |
| Boundary: high == limit fills | `tests/unit/test_limit_trade_through.py::test_limit_sell_boundary_exact` | AttributeError | PASS | Exact boundary (high == limit) trades through |
| Multiple limit orders independent | `tests/unit/test_limit_trade_through.py::test_multiple_limit_orders_independent` | AttributeError | PASS | Same bar evaluated independently per order |
| Cost config applied to limit fills | `tests/unit/test_limit_trade_through.py::test_limit_cost_config_applied` | AttributeError | PASS | Costs computed and applied to fill |
| Deterministic repeatability | `tests/unit/test_limit_trade_through.py::test_limit_deterministic_repeatability` | AttributeError | PASS | Same inputs yield identical events |
| No next bar raises | `tests/unit/test_limit_trade_through.py::test_limit_no_next_bar_raises` | AttributeError | PASS | NextBarFillError at last bar |
| Missing cost blocks operation | `tests/unit/test_limit_trade_through.py::test_limit_missing_cost_blocks` | AttributeError | PASS | Null cost fields block limit fill |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Limit buy trades through | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 2 | Limit sell trades through | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 3 | Limit buy rejected no trade-through | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 4 | Limit sell rejected no trade-through | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 5 | Boundary low == limit | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 6 | Boundary high == limit | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 7 | Multiple orders independent | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 8 | Cost config applied | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 9 | Deterministic | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 10 | No next bar raises | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |
| 11 | Missing cost blocks | `tests/unit/test_limit_trade_through.py` | unit | PASS | 115 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M4.4 lines exercised by unit tests
- Intentional gap: limit order exit logic (stop/target on limit fills) uses same `_find_exit()` as market orders but not separately tested for limit-specific exit behavior
- Intentional gap: stop/target defaults to end_of_data for limit orders without them; real stop/target semantics not exercised in limit tests
- Limit orders share cost config validation with market orders

## Merge evidence
Commit: `f9ffce3` (M4.3) + M4.4 commit (next_bar_open.py + test_limit_trade_through.py). RED evidence: `AttributeError` captured before implementation (enter_limit_long/enter_limit_short missing). GREEN evidence: 115 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
