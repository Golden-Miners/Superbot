# TDD Evidence Report — M8.4 Experiment Registry: Data/Code/Strategy/Parameter/Cost/Config Refs

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.4` ("Experiment registry/data-code-strategy-parameter-cost-config refs").

## User journeys
- As a researcher, I want to register experiments linking code (repo/commit/path), strategy (name/version), parameters, cost, and config refs
- As a researcher, I want to look up all artifacts for an experiment by id
- As a researcher, I want to find experiments using a given code commit
- As a researcher, I want to find experiments using a given strategy name+version
- As a researcher, I want to find experiments using a given parameter window
- As a researcher, I want missing refs to return None rather than crash
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| ExperimentRegistry creation | `tests/unit/test_experiment_registry.py::test_experiment_registry_creates` | ModuleNotFoundError | PASS | Registry instantiates |
| Register experiment | `tests/unit/test_experiment_registry.py::test_register_experiment` | ModuleNotFoundError | PASS | Experiment registered and retrievable |
| Get experiment refs | `tests/unit/test_experiment_registry.py::test_get_experiment_refs` | ModuleNotFoundError | PASS | All refs (code, strategy, parameters, cost, config) returned |
| Unknown experiment | `tests/unit/test_experiment_registry.py::test_get_unknown_experiment` | ModuleNotFoundError | PASS | Unknown id returns None |
| Find by code | `tests/unit/test_experiment_registry.py::test_find_experiments_by_code` | ModuleNotFoundError | PASS | Experiments sharing a code commit found |
| Find by strategy | `tests/unit/test_experiment_registry.py::test_find_experiments_by_strategy` | ModuleNotFoundError | PASS | Experiments sharing a strategy name+version found |
| Find by parameter | `tests/unit/test_experiment_registry.py::test_find_experiments_by_parameter` | ModuleNotFoundError | PASS | Experiments sharing a parameter window found |
| Deterministic | `tests/unit/test_experiment_registry.py::test_experiment_registry_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| CodeRef creation | `tests/unit/test_experiment_registry.py::test_code_ref_creates` | ModuleNotFoundError | PASS | CodeRef stores repo/commit/path |
| StrategyRef creation | `tests/unit/test_experiment_registry.py::test_strategy_ref_creates` | ModuleNotFoundError | PASS | StrategyRef stores name/version |
| ParameterRef creation | `tests/unit/test_experiment_registry.py::test_parameter_ref_creates` | ModuleNotFoundError | PASS | ParameterRef stores window/threshold |
| CostRef creation | `tests/unit/test_experiment_registry.py::test_cost_ref_creates` | ModuleNotFoundError | PASS | CostRef stores spread/commission |
| ConfigRef creation | `tests/unit/test_experiment_registry.py::test_config_ref_creates` | ModuleNotFoundError | PASS | ConfigRef stores env/region |
| ExperimentRef creation | `tests/unit/test_experiment_registry.py::test_experiment_ref_creates` | ModuleNotFoundError | PASS | ExperimentRef stores all refs |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Experiment registration | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |
| 2 | Experiment lookup by id | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |
| 3 | Lookup by code commit | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |
| 4 | Lookup by strategy name+version | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |
| 5 | Lookup by parameter window | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_experiment_registry.py` | unit | PASS | 524 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.4 lines exercised by unit tests
- Intentional gap: No persistence of experiment registry — in-memory only
- Intentional gap: No validation that referenced code/commit actually exists

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.experiment_registry'` captured before implementation. GREEN: 524 tests pass, 2 skipped, ruff clean, format clean, working tree clean.