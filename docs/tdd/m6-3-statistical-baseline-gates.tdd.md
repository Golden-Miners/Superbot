# TDD Evidence Report — M6.3 PF/Sharpe/Sortino/DD/trade-count Gates

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.3` ("PF/Sharpe/Sortino/DD/trade-count gates with documented conventions").

## User journeys
- As a researcher, I want versioned gate specification with explicit Decimal thresholds: min_pf, min_sharpe, min_sortino, max_dd_pct, min_win_rate_pct, min_trade_count
- As a researcher, I want gate evaluation against BaselineMetrics from M5.4
- As a researcher, I want gate to pass only when ALL thresholds are met; any failure blocks
- As a researcher, I want each threshold documented with its rationale (PF >= 1.5, Sharpe >= 1.0, Sortino >= 1.0, max DD <= 10%, win rate >= 40%, trade count >= 10)
- As a researcher, I want gate aggregation: all failing gate names reported, not just first
- As a researcher, I want zero trades cannot pass (insufficient evidence regardless of metrics)
- As a researcher, I want threshold boundary: exactly at threshold passes (>= / <= convention)
- As a researcher, I want deterministic: same inputs → same gate result
- As a researcher, I want no discretionary terms — all thresholds explicit numeric values

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| GateSpec versioned | `tests/unit/test_gates.py::test_gate_spec_versioned` | ModuleNotFoundError | PASS | schema_version + spec_id stored |
| All gates pass | `tests/unit/test_gates.py::test_gates_pass_when_all_thresholds_met` | ModuleNotFoundError | PASS | All thresholds met → PASS |
| PF below threshold fails | `tests/unit/test_gates.py::test_gates_fail_when_profit_factor_below_threshold` | ModuleNotFoundError | PASS | PF below threshold → FAIL with "min_pf" |
| DD above threshold fails | `tests/unit/test_gates.py::test_gates_fail_when_drawdown_exceeds_threshold` | ModuleNotFoundError | PASS | DD above threshold → FAIL with "max_dd_pct" |
| Trade count below threshold | `tests/unit/test_gates.py::test_gates_fail_when_trade_count_below_threshold` | ModuleNotFoundError | PASS | Count below threshold → FAIL with "min_trade_count" |
| Threshold boundary passes | `tests/unit/test_gates.py::test_threshold_boundary_passes` | ModuleNotFoundError | PASS | Exactly at threshold → PASS (>= / <=) |
| Zero trades cannot pass | `tests/unit/test_gates.py::test_zero_trades_cannot_pass` | ModuleNotFoundError | PASS | Zero trades → FAIL regardless of metrics |
| Deterministic gate result | `tests/unit/test_gates.py::test_deterministic_gate_result` | ModuleNotFoundError | PASS | Same inputs → identical result |
| Multiple failures all reported | `tests/unit/test_gates.py::test_multiple_gate_failures_all_reported` | ModuleNotFoundError | PASS | All failing gates reported |
| Decimal fields validation | `tests/unit/test_gates.py::test_gate_spec_decimal_fields_must_be_decimal` | ModuleNotFoundError | PASS | Non-Decimal fields raise ValueError |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | GateSpec versioned | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 2 | Gate evaluation pass/fail | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 3 | Threshold boundary (>= / <=) | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 4 | Zero trades blocked | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 5 | All gate failures reported | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 6 | Deterministic evaluation | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |
| 7 | Decimal validation | `tests/unit/test_gates.py` | unit | PASS | 264 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.3 lines exercised by unit tests
- Intentional gap: gate spec decimal fields validated at construction; parameter fields (non-decimal) not type-validated
- Intentional gap: gate persistence (save/load to disk) not implemented — in-memory only
- Intentional gap: adaptive threshold adjustment not implemented — thresholds are fixed per spec
- `OppositeSignalError` defined in stale_pending_signals but not raised (intentional gap noted in M5.6)

## Merge evidence
Commit: `5574f60` (M6.1) + M6.2 commit `0de9615` + M6.3 commit (gates.py + test_gates.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.gates` missing). GREEN evidence: 264 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
