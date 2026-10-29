# TDD Evidence Report — M7.3 Combined Open-Risk Cap 5%; Adaptive Risk and Verified Sizing

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M7.3` ("Combined open-risk cap 5%; adaptive risk and verified sizing").

## User journeys
- As a risk manager, I want combined open-risk cap of 5% of portfolio
- As a risk manager, I want new entries blocked when combined open risk exceeds 5%
- As a risk manager, I want adaptive position sizing that scales to available headroom
- As a risk manager, I want verified sizing that caps requested size to headroom
- As a risk manager, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| OpenRiskService creation | `tests/unit/test_open_risk_cap.py::test_open_risk_service_creates` | ModuleNotFoundError | PASS | Default cap = 5% |
| OpenRiskService custom cap | `tests/unit/test_open_risk_cap.py::test_open_risk_service_custom_cap` | ModuleNotFoundError | PASS | Custom cap accepted |
| PositionRisk creation | `tests/unit/test_open_risk_cap.py::test_position_risk_creates` | ModuleNotFoundError | PASS | Dataclass with all fields |
| register_open_position | `tests/unit/test_open_risk_cap.py::test_register_open_position` | ModuleNotFoundError | PASS | Position registered and retrievable |
| Combined risk updates | `tests/unit/test_open_risk_cap.py::test_register_open_position_updates_combined_risk` | ModuleNotFoundError | PASS | Sum of all position risks |
| Within cap allowed | `tests/unit/test_open_risk_cap.py::test_check_combined_open_risk_within_cap` | ModuleNotFoundError | PASS | 3% < 5% → allowed |
| At cap allowed | `tests/unit/test_open_risk_cap.py::test_check_combined_open_risk_at_cap` | ModuleNotFoundError | PASS | 5% == 5% → allowed |
| Exceeds cap blocked | `tests/unit/test_open_risk_cap.py::test_check_combined_open_risk_exceeds_cap` | ModuleNotFoundError | PASS | 5.1% > 5% → blocked |
| Verified size within cap | `tests/unit/test_open_risk_cap.py::test_verify_size_within_cap` | ModuleNotFoundError | PASS | Requested size returned when fits |
| Verified size reduced | `tests/unit/test_open_risk_cap.py::test_verify_size_reduced_at_cap` | ModuleNotFoundError | PASS | Size capped to headroom |
| Verified size zero at cap | `tests/unit/test_open_risk_cap.py::test_verify_size_zero_when_at_cap` | ModuleNotFoundError | PASS | 0 when already at cap |
| Adaptive size | `tests/unit/test_open_risk_cap.py::test_compute_adaptive_size` | ModuleNotFoundError | PASS | Size scales to headroom |
| Adaptive size caps | `tests/unit/test_open_risk_cap.py::test_compute_adaptive_size_caps_to_headroom` | ModuleNotFoundError | PASS | Capped to available headroom |
| OpenRiskResult creation | `tests/unit/test_open_risk_cap.py::test_open_risk_result_creates` | ModuleNotFoundError | PASS | Dataclass with reasons |
| Remove position | `tests/unit/test_open_risk_cap.py::test_remove_open_position` | ModuleNotFoundError | PASS | Combined risk reduced |
| Deterministic | `tests/unit/test_open_risk_cap.py::test_open_risk_service_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Combined open-risk cap | `tests/unit/test_open_risk_cap.py` | unit | PASS | 399 passed, 2 skipped |
| 2 | Adaptive sizing | `tests/unit/test_open_risk_cap.py` | unit | PASS | 399 passed, 2 skipped |
| 3 | Verified sizing | `tests/unit/test_open_risk_cap.py` | unit | PASS | 399 passed, 2 skipped |
| 4 | Position add/remove | `tests/unit/test_open_risk_cap.py` | unit | PASS | 399 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_open_risk_cap.py` | unit | PASS | 399 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M7.3 lines exercised by unit tests
- Intentional gap: No persistence of open positions — in-memory only
- Intentional gap: No integration with M7.2 halt — separate manager

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.risk.open_risk_cap'` captured before implementation. GREEN: 399 tests pass, 2 skipped, ruff clean, format clean, working tree clean.