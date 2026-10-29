# TDD Evidence Report — M5.2 Trend-Following / Pullback Definition

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.2` ("Trend-following/pullback definition and tests").

## User journeys
- As a researcher, I want deterministic trend detection: HH/HL = uptrend, LH/LL = downtrend, neither = ranging
- As a researcher, I want fewer-than-lookback bars to return UNKNOWN trend (never guess)
- As a researcher, I want pullback detection: retracement depth within explicit [min, max] % of impulse move
- As a researcher, I want pullback entry: long in uptrend on pullback to support, short in downtrend on pullback to resistance
- As a researcher, I want bounce confirmation (close beyond the pullback extreme) before signaling
- As a researcher, I want versioned rule schema: TrendSpec and PullbackSpec carry schema_version and rule_id
- As a researcher, I want same inputs to yield identical trend/pullback signals (deterministic)
- As a researcher, I want no discretionary terms — all thresholds are explicit numeric parameters

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Uptrend detection | `tests/unit/test_trend_following.py::test_uptrend_higher_highs_higher_lows` | ModuleNotFoundError | PASS | HH/HL over lookback = UPTREND |
| Downtrend detection | `tests/unit/test_trend_following.py::test_downtrend_lower_highs_lower_lows` | ModuleNotFoundError | PASS | LH/LL over lookback = DOWNTREND |
| Ranging detection | `tests/unit/test_trend_following.py::test_ranging_market` | ModuleNotFoundError | PASS | Neither HH/HL nor LH/LL = RANGING |
| Insufficient bars → UNKNOWN | `tests/unit/test_trend_following.py::test_insufficient_bars_unknown` | ModuleNotFoundError | PASS | <lookback bars returns UNKNOWN |
| Pullback in uptrend | `tests/unit/test_trend_following.py::test_pullback_in_uptrend` | ModuleNotFoundError | PASS | Retracement in [min,max] depth + bounce = entry_long |
| No pullback in ranging | `tests/unit/test_trend_following.py::test_no_pullback_in_ranging` | ModuleNotFoundError | PASS | Ranging trend → no pullback signal |
| Depth out of range | `tests/unit/test_trend_following.py::test_pullback_depth_out_of_range` | ModuleNotFoundError | PASS | Depth > max_depth_pct → no signal |
| Trend-following entry long | `tests/unit/test_trend_following.py::test_trend_following_entry_long` | ModuleNotFoundError | PASS | Uptrend pullback → entry_long signal |
| Trend-following entry short | `tests/unit/test_trend_following.py::test_trend_following_entry_short` | ModuleNotFoundError | PASS | Downtrend pullback → entry_short signal |
| No entry in ranging | `tests/unit/test_trend_following.py::test_trend_following_no_entry_ranging` | ModuleNotFoundError | PASS | Ranging → no entry signal |
| TrendSpec versioned | `tests/unit/test_trend_following.py::test_trend_spec_versioned` | ModuleNotFoundError | PASS | schema_version + rule_id stored |
| PullbackSpec versioned | `tests/unit/test_trend_following.py::test_pullback_spec_versioned` | ModuleNotFoundError | PASS | schema_version + rule_id stored |
| Deterministic trend | `tests/unit/test_trend_following.py::test_deterministic_trend` | ModuleNotFoundError | PASS | Same inputs → identical trend |
| Deterministic pullback | `tests/unit/test_trend_following.py::test_deterministic_pullback` | ModuleNotFoundError | PASS | Same inputs → identical signal |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Trend detection HH/HL → uptrend | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 2 | Trend detection LH/LL → downtrend | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 3 | Ranging detection | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 4 | Unknown trend for insufficient bars | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 5 | Pullback depth within [min,max] | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 6 | Bounce confirmation required | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 7 | Entry_long in uptrend pullback | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 8 | Entry_short in downtrend pullback | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 9 | Deterministic replay | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |
| 10 | Versioned rule schema | `tests/unit/test_trend_following.py` | unit | PASS | 187 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.2 lines exercised by unit tests
- Intentional gap: trend detection uses strict consecutive HH/HL comparison; real-world trends may have minor pullbacks within the trend — could be relaxed with a tolerance parameter later
- Intentional gap: pullback depth measured from recent high/low to current bar low/high; alternative methods (Fibonacci levels from swing points) could be added
- Intentional gap: `ma_period` field in TrendSpec is stored but not yet used in detection logic — reserved for future moving-average confirmation
- Trend and pullback detected from historical bars only (current bar excluded) — prevents look-ahead bias

## Merge evidence
Commit: `e4920d6` (M5.1) + M5.2 commit (trend_following.py + test_trend_following.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy` module missing). GREEN evidence: 187 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
