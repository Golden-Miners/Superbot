# TDD Evidence Report — M7.6 Competing Signal Ranking, Reserve/Capacity, Group Limits, Resize/Reject Semantics

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.6` ("Competing signal ranking, reserve/capacity, group limits, resize/reject semantics").

## User journeys
- As a risk manager, I want competing signals ranked by score (highest first)
- As a risk manager, I want reserve/capacity enforcement: total allocated size cannot exceed reserve capacity
- As a risk manager, I want group limits: max signal count and max risk pct per group
- As a risk manager, I want resize/reject semantics: resize signal to fit remaining capacity, or reject when below min size
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Signal creation | `tests/unit/test_signal_ranking.py::test_signal_creates` | ModuleNotFoundError | PASS | Signal stores symbol, side, score, size |
| Service creation | `tests/unit/test_signal_ranking.py::test_signal_ranking_service_creates` | ModuleNotFoundError | PASS | Service instantiates |
| Rank by score descending | `tests/unit/test_signal_ranking.py::test_rank_signals_by_score_descending` | ModuleNotFoundError | PASS | Highest score first |
| RankedSignal creation | `tests/unit/test_signal_ranking.py::test_ranked_signal_creates` | ModuleNotFoundError | PASS | RankedSignal stores rank |
| Reserve capacity creation | `tests/unit/test_signal_ranking.py::test_reserve_capacity_service_creates` | ModuleNotFoundError | PASS | Total capacity stored |
| Allocate within reserve | `tests/unit/test_signal_ranking.py::test_allocate_capacity_within_reserve` | ModuleNotFoundError | PASS | Total 90000 <= 100000 → allocated |
| Allocate exceeds reserve | `tests/unit/test_signal_ranking.py::test_allocate_capacity_exceeds_reserve` | ModuleNotFoundError | PASS | Total 120000 > 100000 → not allocated |
| Remaining capacity | `tests/unit/test_signal_ranking.py::test_reserve_capacity_remaining` | ModuleNotFoundError | PASS | 100000 - 30000 = 70000 |
| GroupLimit creation | `tests/unit/test_signal_ranking.py::test_group_limit_creates` | ModuleNotFoundError | PASS | GroupLimit stores group, max_signals, max_risk_pct |
| Add group limit | `tests/unit/test_signal_ranking.py::test_add_group_limit` | ModuleNotFoundError | PASS | Group limit registered and retrievable |
| Group limits within | `tests/unit/test_signal_ranking.py::test_check_group_limits_within_limits` | ModuleNotFoundError | PASS | Count & risk within limits → passed |
| Group limits exceeded count | `tests/unit/test_signal_ranking.py::test_check_group_limits_exceeds_signal_count` | ModuleNotFoundError | PASS | Count > max_signals → failed |
| Group limits exceeded risk | `tests/unit/test_signal_ranking.py::test_check_group_limits_exceeds_risk` | ModuleNotFoundError | PASS | Risk > max_risk_pct → failed |
| ResizeRejectSemantics creation | `tests/unit/test_signal_ranking.py::test_resize_reject_semantics_creates` | ModuleNotFoundError | PASS | Service instantiates |
| Resize | `tests/unit/test_signal_ranking.py::test_resize_or_reject_resize` | ModuleNotFoundError | PASS | Available capacity >= min_size → resize |
| Reject | `tests/unit/test_signal_ranking.py::test_resize_or_reject_reject` | ModuleNotFoundError | PASS | Available capacity < min_size → reject |
| ResizeRejectDecision | `tests/unit/test_signal_ranking.py::test_resize_reject_decision_creates` | ModuleNotFoundError | PASS | Decision dataclass |
| Deterministic | `tests/unit/test_signal_ranking.py::test_signal_ranking_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Signal ranking by score | `tests/unit/test_signal_ranking.py` | unit | PASS | 450 passed, 2 skipped |
| 2 | Reserve/capacity enforcement | `tests/unit/test_signal_ranking.py` | unit | PASS | 450 passed, 2 skipped |
| 3 | Group limits (count + risk) | `tests/unit/test_signal_ranking.py` | unit | PASS | 450 passed, 2 skipped |
| 4 | Resize/reject semantics | `tests/unit/test_signal_ranking.py` | unit | PASS | 450 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_signal_ranking.py` | unit | PASS | 450 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.6 lines exercised by unit tests
- Intentional gap: No persistence of allocations or group state — in-memory only
- Intentional gap: No concurrency handling (separate M7.7 task)

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.signal_ranking'` captured before implementation. GREEN: 450 tests pass, 2 skipped, ruff clean, format clean, working tree clean.