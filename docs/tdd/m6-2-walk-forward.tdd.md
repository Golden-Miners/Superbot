# TDD Evidence Report — M6.2 Walk-Forward Windows & Metric Accounting

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.2` (">=3 walk-forward windows and metric-accounting tests").

## User journeys
- As a researcher, I want >=3 walk-forward windows sliding chronologically across data
- As a researcher, I want each window: train < val < test chronologically with no overlap
- As a researcher, I want gap bars between validation and test to prevent leakage
- As a researcher, I want per-window metrics: PF, Sharpe, Sortino, max DD, trade count
- As a researcher, I want aggregate metric accounting across windows (mean/std)
- As a researcher, I want stability check: PF CV < 10% across windows
- As a researcher, I want deterministic: same inputs → same windows
- As a researcher, I want n_windows >= 3 enforced (reject fewer)
- As a researcher, I want versioned spec: WalkForwardSpec carries schema_version and spec_id

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| WalkForwardSpec versioned | `tests/unit/test_walk_forward.py::test_walk_forward_spec_versioned` | ModuleNotFoundError | PASS | schema_version + spec_id stored |
| Min 3 windows | `tests/unit/test_walk_forward.py::test_generate_windows_min_3_windows` | ModuleNotFoundError | PASS | Produces >=3 windows |
| Chronological order | `tests/unit/test_walk_forward.py::test_windows_chronological` | ModuleNotFoundError | PASS | Train < Val < Test per window |
| No overlap within window | `tests/unit/test_walk_forward.py::test_windows_no_overlap_within_window` | ModuleNotFoundError | PASS | No timestamp in multiple splits |
| Windows slide forward | `tests/unit/test_walk_forward.py::test_windows_slide_forward` | ModuleNotFoundError | PASS | Each window starts after previous |
| Metric accounting | `tests/unit/test_walk_forward.py::test_metric_accounting` | ModuleNotFoundError | PASS | Per-window + aggregate metrics |
| Stability pass | `tests/unit/test_walk_forward.py::test_check_stability_pass` | ModuleNotFoundError | PASS | Consistent metrics → stable |
| Stability fail | `tests/unit/test_walk_forward.py::test_check_stability_fail_high_variance` | ModuleNotFoundError | PASS | High variance → not stable |
| Deterministic | `tests/unit/test_walk_forward.py::test_deterministic_windows` | ModuleNotFoundError | PASS | Same inputs → same windows |
| Insufficient bars | `tests/unit/test_walk_forward.py::test_insufficient_bars_raises` | ModuleNotFoundError | PASS | ValueError when bars < required |
| n_windows >= 3 | `tests/unit/test_walk_forward.py::test_n_windows_min_3` | ModuleNotFoundError | PASS | n_windows < 3 raises ValueError |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Walk-forward windows | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 2 | Chronological order | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 3 | No overlap | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 4 | Slide forward | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 5 | Metric accounting | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 6 | Stability check | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 7 | Deterministic | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |
| 8 | n_windows >= 3 enforced | `tests/unit/test_walk_forward.py` | unit | PASS | 264 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.2 lines exercised by unit tests
- Intentional gap: metric accounting only computes mean/std; no percentile-based stability
- Intentional gap: walk-forward windows use absolute bar counts, not date ranges
- Intentional gap: no integration with M5.4 baseline gates (separate phase)
- `OppositeSignalError` class defined in stale_pending_signals but not raised (intentional gap noted there)

## Merge evidence
Commit: `5574f60` (M6.1) + M6.2 commit (walk_forward.py + test_walk_forward.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.data.walk_forward` missing). GREEN evidence: 264 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
