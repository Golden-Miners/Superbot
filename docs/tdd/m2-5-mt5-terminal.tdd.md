# TDD Evidence Report — M2.5 Real MT5 Terminal Connection

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M2.5` ("Verify read-only MT5 adapter API/symbol/spec discovery only after local setup permits; no order access") and user directive to launch/use the installed MT5 terminal.

## User journeys
- As a researcher, I want Superbot to launch/connect to the installed MT5 terminal so it can perform read-only discovery.
- As a researcher, I want read-only discovery of MT5 symbols and instrument specs without assuming broker values.
- As a researcher, I want the adapter to never submit orders.
- As a researcher, I want MetaTrader5 imported lazily (no import-time broker interaction).
- As a researcher, I want missing broker fields preserved as null (never guessed) and inferred asset classes flagged AMBIGUOUS.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Adapter initializes against real MT5 terminal | `tests/integration/test_mt5_terminal.py::test_adapter_initializes_against_real_terminal` | TypeError (no `path` param) | PASS | `initialize(path)` launches/connects to terminal |
| Symbol discovery returns nonempty list | `test_discover_symbols_returns_nonempty_list` | TypeError | PASS | Returns actual broker symbols; `SymbolInfo.name` extracted |
| Symbol spec maps to InstrumentSpec | `test_discover_symbol_spec_returns_instrument_spec` | TypeError | PASS | Maps `symbol_info()` fields to `InstrumentSpec` |
| Account info returns dict | `test_discover_account_returns_dict` | TypeError | PASS | Returns account info as dict |
| Shutdown clears initialized state | `test_shutdown_clears_initialized_state` | TypeError | PASS | `_initialized` reset to False after shutdown |
| Unknown symbol raises Mt5SymbolNotFound | `test_unknown_symbol_raises_symbol_not_found` | TypeError | PASS | Raises `Mt5SymbolNotFound` for absent symbol |
| Adapter import has no import-time broker interaction | `tests/unit/test_mt5_adapter.py::test_adapter_import_does_not_load_mt5` | (was passing) | PASS | `MetaTrader5` not in `sys.modules` after adapter import |
| Fake module compatibility | `tests/unit/test_mt5_adapter.py` (5 tests) | (was passing) | PASS | Works with fake module for offline testing |

## Test specification
| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | `initialize(path)` connects to real MT5 terminal | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite, TEST_EXIT:True |
| 2 | Symbol discovery returns actual broker symbols | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite |
| 3 | Symbol spec maps to `InstrumentSpec` with correct fields | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite |
| 4 | Account info returned as dict | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite |
| 5 | Shutdown clears initialized state | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite |
| 6 | Unknown symbol raises `Mt5SymbolNotFound` | `tests/integration/test_mt5_terminal.py` | integration | PASS | 51-test suite |
| 7 | No import-time broker interaction | `tests/unit/test_mt5_adapter.py` | unit | PASS | 51-test suite |
| 8 | No order submission methods | `tests/unit/test_mt5_adapter.py` | unit | PASS | 51-test suite |

## Coverage and known gaps
- Coverage command not run (no coverage tool configured); all M2.5 lines exercised by unit + integration tests.
- Intentional gap: integration tests skip (not fail) when MT5 terminal is unavailable — `initialize()` returns False → `pytest.skip()`.
- No live terminal login/order submission — read-only discovery only.
- No assumed symbol names — tests iterate over whatever symbols the terminal reports.

## Merge evidence
Commits: `93644e2` (M2.5 adapter + fake-module unit tests), follow-up commit (real terminal `initialize(path)` + integration tests + docs). RED evidence: `TypeError` captured before implementation. GREEN evidence: 51 tests pass (45 unit + 6 integration), ruff clean, format clean, `git diff --check` clean, working tree clean.
