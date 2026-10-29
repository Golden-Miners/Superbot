# TDD Evidence Report — M7.5 ATR-Relative Volatility and Hard Blocks; Thresholds OPEN

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.5` ("ATR-relative volatility and hard blocks; thresholds OPEN, never guessed").

## User journeys
- As a risk manager, I want ATR-relative volatility computed from price data (ATR / current_price * 100)
- As a risk manager, I want volatility block: pause trading when ATR-rel vol exceeds configured threshold
- As a risk manager, I want hard blocks: pause trading when any configured hard-limit metric is breached
- As a risk manager, I want all thresholds OPEN configuration inputs — never hardcoded or guessed
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| ATRReading creation | `tests/unit/test_atr_volatility.py::test_atr_reading_creates` | ModuleNotFoundError | PASS | ATRReading stores atr, price, rel vol |
| compute_atr | `tests/unit/test_atr_volatility.py::test_compute_atr` | ModuleNotFoundError | PASS | ATR = mean of True Range values |
| ATR-relative volatility | `tests/unit/test_atr_volatility.py::test_compute_atr_relative_volatility` | ModuleNotFoundError | PASS | ATR / price * 100 |
| Service creation | `tests/unit/test_atr_volatility.py::test_atr_volatility_service_creates` | ModuleNotFoundError | PASS | Configurable threshold |
| Volatility block below threshold | `tests/unit/test_atr_volatility.py::test_compute_volatility_block_not_blocked` | ModuleNotFoundError | PASS | vol <= threshold → not blocked |
| Volatility block above threshold | `tests/unit/test_atr_volatility.py::test_compute_volatility_block_blocked` | ModuleNotFoundError | PASS | vol > threshold → blocked |
| Volatility block at threshold | `tests/unit/test_atr_volatility.py::test_volatility_block_at_threshold` | ModuleNotFoundError | PASS | vol == threshold → not blocked |
| HardBlock creation | `tests/unit/test_atr_volatility.py::test_hard_block_creates` | ModuleNotFoundError | PASS | HardBlock stores metric, threshold, breached |
| compute_hard_block not breached | `tests/unit/test_atr_volatility.py::test_compute_hard_block_not_breached` | ModuleNotFoundError | PASS | value <= threshold → not breached |
| compute_hard_block breached | `tests/unit/test_atr_volatility.py::test_compute_hard_block_breached` | ModuleNotFoundError | PASS | value > threshold → breached |
| HardBlockService creation | `tests/unit/test_atr_volatility.py::test_hard_block_service_creates` | ModuleNotFoundError | PASS | Service instantiates |
| Add hard block | `tests/unit/test_atr_volatility.py::test_add_hard_block` | ModuleNotFoundError | PASS | Block registered and retrievable |
| Check hard blocks none breached | `tests/unit/test_atr_volatility.py::test_check_hard_blocks_none_breached` | ModuleNotFoundError | PASS | All below thresholds → not blocked |
| Check hard blocks breached | `tests/unit/test_atr_volatility.py::test_check_hard_blocks_breached` | ModuleNotFoundError | PASS | Any above threshold → blocked |
| Thresholds never hardcoded | `tests/unit/test_atr_volatility.py::test_thresholds_never_hardcoded` | ModuleNotFoundError | PASS | Thresholds are config inputs |
| Deterministic | `tests/unit/test_atr_volatility.py::test_atr_volatility_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| VolatilityBlockResult creation | `tests/unit/test_atr_volatility.py::test_volatility_block_result_creates` | ModuleNotFoundError | PASS | Result dataclass |
| HardBlockResult creation | `tests/unit/test_atr_volatility.py::test_hard_block_result_creates` | ModuleNotFoundError | PASS | Result dataclass |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | ATR computation | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |
| 2 | ATR-relative volatility | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |
| 3 | Volatility block | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |
| 4 | Hard blocks | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |
| 5 | Thresholds OPEN | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_atr_volatility.py` | unit | PASS | 431 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.5 lines exercised by unit tests
- Intentional gap: No persistence of ATR readings or hard-block state — in-memory only
- Intentional gap: Thresholds remain OPEN — caller must supply them; no defaults

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.atr_volatility'` captured before implementation. GREEN: 431 tests pass, 2 skipped, ruff clean, format clean, working tree clean.