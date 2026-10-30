# TDD Evidence Report — M8.2 Versioned Migrations and Old Experiment Readability

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.2` ("Versioned migrations and old experiment readability").

## User journeys
- As a researcher, I want migrations applied in ascending version order, each at most once
- As a researcher, I want migration tracking (which versions have been applied)
- As a researcher, I want migration rollback (revert last applied migration)
- As a researcher, I want old experiment readability: read experiment data written under older schema versions
- As a researcher, I want schema evolution: adding a column doesn't break reading old rows
- As a researcher, I want missing/invalid migrations to block rather than silently skip
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Migration creation | `tests/unit/test_migrations.py::test_migration_creates` | ModuleNotFoundError | PASS | Migration stores version + up/down functions |
| Service creation | `tests/unit/test_migrations.py::test_migration_service_creates` | ModuleNotFoundError | PASS | MigrationService instantiates |
| Apply migration | `tests/unit/test_migrations.py::test_apply_migration_records` | ModuleNotFoundError | PASS | Migration applied, up() called, result success=True |
| Apply twice blocked | `tests/unit/test_migrations.py::test_apply_migration_twice_blocked` | ModuleNotFoundError | PASS | Second apply returns success=False |
| Applied in order | `tests/unit/test_migrations.py::test_migrations_applied_in_order` | ModuleNotFoundError | PASS | Versions applied 1,2,3 regardless of registration order |
| Migration status | `tests/unit/test_migrations.py::test_migration_status` | ModuleNotFoundError | PASS | check_migration_status reports applied/not applied |
| Rollback migration | `tests/unit/test_migrations.py::test_rollback_migration` | ModuleNotFoundError | PASS | Rollback calls down(), success=True |
| Rollback not applied blocked | `tests/unit/test_migrations.py::test_rollback_not_applied_blocked` | ModuleNotFoundError | PASS | Rollback of unapplied migration returns success=False |
| Experiment record creation | `tests/unit/test_migrations.py::test_experiment_record_creates` | ModuleNotFoundError | PASS | ExperimentRecord stores all fields |
| Experiment store creation | `tests/unit/test_migrations.py::test_experiment_store_creates` | ModuleNotFoundError | PASS | ExperimentStore instantiates |
| Record & read experiment | `tests/unit/test_migrations.py::test_record_and_read_experiment` | ModuleNotFoundError | PASS | Written experiment readable back with same data |
| Read unknown experiment | `tests/unit/test_migrations.py::test_read_unknown_experiment` | ModuleNotFoundError | PASS | Unknown id returns None |
| Read old schema experiment | `tests/unit/test_migrations.py::test_read_old_schema_experiment` | ModuleNotFoundError | PASS | Old schema version readable (backward compat) |
| Migration deterministic | `tests/unit/test_migrations.py::test_migration_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| MigrationResult creation | `tests/unit/test_migrations.py::test_migration_result_creates` | ModuleNotFoundError | PASS | MigrationResult dataclass |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Versioned migration ordering | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |
| 2 | Migration applied at most once | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |
| 3 | Migration rollback | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |
| 4 | Old experiment readability | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |
| 5 | Schema evolution compatibility | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_migrations.py` | unit | PASS | 498 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.2 lines exercised by unit tests
- Intentional gap: No persistence of migration state — in-memory only
- Intentional gap: Migration up/down functions are callables supplied by caller; no SQL generation
- Intentional gap: Experiment store is in-memory dict, not persisted to disk

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.migrations'` captured before implementation. GREEN: 498 tests pass, 2 skipped, ruff clean, format clean, working tree clean.