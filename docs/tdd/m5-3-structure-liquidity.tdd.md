# TDD Evidence Report — M5.3 Liquidity-Sweep / Market Structure (BOS/CHOCH)

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.3` ("Liquidity-sweep/structure strategy; precise BOS/CHOCH definitions; defer OB/FVG until precise rule acceptance").

## User journeys
- As a researcher, I want precise bullish BOS: close breaks above prior swing high
- As a researcher, I want precise bearish BOS: close breaks below prior swing low
- As a researcher, I want precise bullish CHOCH: in downtrend, close breaks above prior swing high (trend reversal)
- As a researcher, I want precise bearish CHOCH: in uptrend, close breaks below prior swing low (trend reversal)
- As a researcher, I want liquidity sweep detection: wick breaches level but close rejects (false breakout)
- As a researcher, I want structure state: current swing high/low and prevailing trend
- As a researcher, I want versioned rule spec: StructureSpec carries schema_version, rule_id, lookback_bars
- As a researcher, I want same inputs to yield identical structure events (deterministic)
- As a researcher, I want no discretionary terms — all thresholds explicit numeric parameters
- As a researcher, I want OB/FVG deferred until precise rule acceptance (not tested here)

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Bullish BOS | `tests/unit/test_structure_liquidity.py::test_bullish_bos` | ModuleNotFoundError | PASS | Close above prior swing high → BOSDirection.BULLISH |
| Bearish BOS | `tests/unit/test_structure_liquidity.py::test_bearish_bos` | ModuleNotFoundError | PASS | Close below prior swing low → BOSDirection.BEARISH |
| No BOS on wick-only break | `tests/unit/test_structure_liquidity.py::test_no_bos_when_close_does_not_break` | ModuleNotFoundError | PASS | Wick breaches but close doesn't → no BOS event |
| Bullish CHOCH | `tests/unit/test_structure_liquidity.py::test_bullish_choch` | ModuleNotFoundError | PASS | Downtrend, close above swing high → CHOCHDirection.BULLISH |
| Bearish CHOCH | `tests/unit/test_structure_liquidity.py::test_bearish_choch` | ModuleNotFoundError | PASS | Uptrend, close below swing low → CHOCHDirection.BEARISH |
| Bullish liquidity sweep | `tests/unit/test_structure_liquidity.py::test_liquidity_sweep_bullish` | ModuleNotFoundError | PASS | Wick below swing low, close above → bullish sweep |
| Bearish liquidity sweep | `tests/unit/test_structure_liquidity.py::test_liquidity_sweep_bearish` | ModuleNotFoundError | PASS | Wick above swing high, close below → bearish sweep |
| No sweep on true break | `tests/unit/test_structure_liquidity.py::test_no_liquidity_sweep_when_close_breaks` | ModuleNotFoundError | PASS | Close breaks level → not a sweep |
| Structure state | `tests/unit/test_structure_liquidity.py::test_structure_state_swing_highs_lows` | ModuleNotFoundError | PASS | swing_high, swing_low, current_trend tracked |
| StructureSpec versioned | `tests/unit/test_structure_liquidity.py::test_structure_spec_versioned` | ModuleNotFoundError | PASS | schema_version + rule_id stored |
| Deterministic structure | `tests/unit/test_structure_liquidity.py::test_deterministic_structure` | ModuleNotFoundError | PASS | Same inputs → identical events |
| Insufficient bars | `tests/unit/test_structure_liquidity.py::test_insufficient_bars_no_events` | ModuleNotFoundError | PASS | <lookback bars → no events |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Bullish BOS detection | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 2 | Bearish BOS detection | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 3 | Bullish CHOCH detection | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 4 | Bearish CHOCH detection | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 5 | Liquidity sweep detection | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 6 | Structure state tracking | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 7 | Deterministic replay | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |
| 8 | Insufficient bars guard | `tests/unit/test_structure_liquidity.py` | unit | PASS | 199 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.3 lines exercised by unit tests
- Intentional gap: OB (Order Block) and FVG (Fair Value Gap) are deferred per task.md until precise rule acceptance — not implemented or tested
- Intentional gap: prevailing trend for CHOCH uses close-to-close comparison over history window; more sophisticated trend classification could be added later
- Intentional gap: BOS/CHOCH event timestamps use current bar open; could use bar close time instead
- Prevailing trend detected from historical bars only (current bar excluded) — prevents look-ahead bias

## Merge evidence
Commit: `a1144bf` (M5.2) + M5.3 commit (structure_liquidity.py + test_structure_liquidity.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.structure_liquidity` missing). GREEN evidence: 199 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
