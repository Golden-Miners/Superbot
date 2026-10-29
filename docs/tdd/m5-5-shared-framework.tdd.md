# TDD Evidence Report — M5.5 Shared Framework / Versioned Configs

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M5.5` ("Shared framework and versioned configs; no ten LLM strategy agents").

## User journeys
- As a researcher, I want a single shared framework for all strategy rules — no ten LLM strategy agents
- As a researcher, I want versioned strategy configs with schema_version, config_id, rule_refs, parameters
- As a researcher, I want framework registration and retrieval by config_id
- As a researcher, I want dedup: registering duplicate config_id raises StrategyConfigError
- As a researcher, I want config validation: required fields present, rule_refs non-empty
- As a researcher, I want versioned configs: different schema_versions coexist under different config_ids
- As a researcher, I want no discretionary terms — all parameters explicit numeric values
- As a researcher, I want deterministic: same inputs produce identical config lookup

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Singleton framework | `tests/unit/test_shared_framework.py::test_shared_framework_singleton` | ModuleNotFoundError | PASS | One framework instance — no ten LLM agents |
| Register and get | `tests/unit/test_shared_framework.py::test_shared_framework_register_and_get` | ModuleNotFoundError | PASS | Register config, retrieve by config_id |
| Dedup rejects duplicate | `tests/unit/test_shared_framework.py::test_shared_framework_dedup_rejects_duplicate` | ModuleNotFoundError | PASS | Duplicate config_id raises StrategyConfigError |
| Get nonexistent | `tests/unit/test_shared_framework.py::test_shared_framework_get_nonexistent_returns_none` | ModuleNotFoundError | PASS | get() returns None for missing config_id |
| Validates rule_refs | `tests/unit/test_shared_framework.py::test_shared_framework_validates_rule_refs` | ModuleNotFoundError | PASS | Empty rule_refs raises StrategyConfigError |
| Versioned configs coexist | `tests/unit/test_shared_framework.py::test_shared_framework_versioned_configs` | ModuleNotFoundError | PASS | Different schema_versions under different config_ids |
| No ten LLM agents | `tests/unit/test_shared_framework.py::test_shared_framework_no_ten_llm_agents` | ModuleNotFoundError | PASS | Singleton shares state across references |
| all_configs() | `tests/unit/test_shared_framework.py::test_shared_framework_all_configs` | ModuleNotFoundError | PASS | Returns all registered configs |
| Deterministic lookup | `tests/unit/test_shared_framework.py::test_shared_framework_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical config |
| Parameters explicit | `tests/unit/test_shared_framework.py::test_shared_framework_parameters_explicit` | ModuleNotFoundError | PASS | All parameters are explicit numerics |
| config_id required | `tests/unit/test_shared_framework.py::test_shared_framework_config_id_required` | ModuleNotFoundError | PASS | Empty config_id raises StrategyConfigError |
| schema_version required | `tests/unit/test_shared_framework.py::test_shared_framework_schema_version_required` | ModuleNotFoundError | PASS | Empty schema_version raises StrategyConfigError |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Singleton framework | `tests/unit/test_shared_framework.py` | unit | PASS | 225 passed, 2 skipped |
| 2 | Versioned config registration | `tests/unit/test_shared_framework.py` | unit | PASS | 225 passed, 2 skipped |
| 3 | Dedup rejects duplicate | `tests/unit/test_shared_framework.py` | unit | PASS | 225 passed, 2 skipped |
| 4 | Config validation | `tests/unit/test_shared_framework.py` | unit | PASS | 225 passed, 2 skipped |
| 5 | Deterministic lookup | `tests/unit/test_shared_framework.py` | unit | PASS | 225 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M5.5 lines exercised by unit tests
- Intentional gap: config persistence (save/load to disk) not implemented — in-memory only
- Intentional gap: config version migration (upgrading old schema_version to new) not implemented
- Intentional gap: rule_refs are stored as strings but not validated against an actual rule registry
- Singleton pattern uses class-level _instance; tests use SharedStrategyFramework.reset() for isolation

## Merge evidence
Commit: `c4d50c5` (M5.4) + M5.5 commit (shared_framework.py + test_shared_framework.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.strategy.shared_framework` missing). GREEN evidence: 225 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
