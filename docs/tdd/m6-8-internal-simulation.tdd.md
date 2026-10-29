# TDD Evidence Report — M6.8 Internal-Simulation Eligibility and Version Archive Rule

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.8` ("Internal-simulation eligibility and three-failed-validation-attempt version archive rule").

## User journeys
- As a researcher, I want internal-simulation eligibility check with configurable cost-adjusted return %, Sharpe, and max DD thresholds
- As a researcher, I want all criteria to pass for internal simulation to be eligible
- As a researcher, I want failure reasons listed per criterion
- As a researcher, I want version archive rule: track validation attempts per version
- As a researcher, I want version archived after 3 consecutive failed validations
- As a researcher, I want passing validation to reset failure count
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| InternalSimulationConfig defaults | `tests/unit/test_internal_simulation.py::test_internal_simulation_config_creates` | ModuleNotFoundError | PASS | Default thresholds: return=5%, Sharpe=1.0, max DD=15%, max failures=3 |
| InternalSimulationConfig custom | `tests/unit/test_internal_simulation.py::test_internal_simulation_config_custom` | ModuleNotFoundError | PASS | Custom thresholds accepted |
| InternalSimulationResult creation | `tests/unit/test_internal_simulation.py::test_internal_simulation_result_creates` | ModuleNotFoundError | PASS | Dataclass instantiates with all fields |
| All criteria pass | `tests/unit/test_internal_simulation.py::test_evaluate_internal_simulation_eligible_all_pass` | ModuleNotFoundError | PASS | eligible=True, reasons=[] |
| Low cost-adjusted return | `tests/unit/test_internal_simulation.py::test_evaluate_internal_simulation_not_eligible_low_return` | ModuleNotFoundError | PASS | eligible=False, reason mentions return |
| Low Sharpe | `tests/unit/test_internal_simulation.py::test_evaluate_internal_simulation_not_eligible_low_sharpe` | ModuleNotFoundError | PASS | eligible=False, reason mentions Sharpe |
| High max DD | `tests/unit/test_internal_simulation.py::test_evaluate_internal_simulation_not_eligible_high_dd` | ModuleNotFoundError | PASS | eligible=False, reason mentions DD |
| Multiple failures | `tests/unit/test_internal_simulation.py::test_evaluate_internal_simulation_not_eligible_multiple_failures` | ModuleNotFoundError | PASS | eligible=False, 3 reasons |
| Deterministic | `tests/unit/test_internal_simulation.py::test_internal_simulation_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Boundary at threshold | `tests/unit/test_internal_simulation.py::test_internal_simulation_boundary_at_threshold` | ModuleNotFoundError | PASS | Values exactly at threshold pass |
| Boundary below threshold | `tests/unit/test_internal_simulation.py::test_internal_simulation_boundary_below_threshold` | ModuleNotFoundError | PASS | Values just below threshold fail |
| VersionArchiveRule creation | `tests/unit/test_internal_simulation.py::test_version_archive_rule_creates` | ModuleNotFoundError | PASS | Rule instantiates |
| Records attempts | `tests/unit/test_internal_simulation.py::test_version_archive_rule_records_attempts` | ModuleNotFoundError | PASS | Tracks failures per version |
| Pass resets failures | `tests/unit/test_internal_simulation.py::test_version_archive_rule_passing_resets_failures` | ModuleNotFoundError | PASS | Passing validation resets failure count |
| Three failures archive | `tests/unit/test_internal_simulation.py::test_version_archive_rule_three_failures_archives` | ModuleNotFoundError | PASS | 3 consecutive failures → archived |
| Not archived before 3 | `tests/unit/test_internal_simulation.py::test_version_archive_rule_not_archived_before_three_failures` | ModuleNotFoundError | PASS | < 3 failures → not archived |
| record_validation_attempt | `tests/unit/test_internal_simulation.py::test_record_validation_attempt_function` | ModuleNotFoundError | PASS | Function records attempt |
| is_version_archived | `tests/unit/test_internal_simulation.py::test_is_version_archived_function` | ModuleNotFoundError | PASS | Function checks archive status |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Internal simulation eligibility | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 2 | Cost-adjusted return check | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 3 | Sharpe check | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 4 | Max DD check | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 5 | Version archive rule | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 6 | Pass resets failures | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |
| 7 | Deterministic results | `tests/unit/test_internal_simulation.py` | unit | PASS | 353 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.8 lines exercised by unit tests
- Intentional gap: No integration with M6.3 gates — internal simulation uses standalone criteria
- Intentional gap: No persistence of version archive state — in-memory only

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.strategy.internal_simulation'` captured before implementation. GREEN: 353 tests pass, 2 skipped, ruff clean, format clean, working tree clean.