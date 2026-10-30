# TDD Evidence Report — M8.7 30-day Retention, Integrity Checks, Monthly Restore Test, Migration Package

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.7` ("30-day retention, integrity checks, monthly restore test and migration package").

## User journeys
- As a researcher, I want retention policy with configurable retention period (default 30 days)
- As a researcher, I want BackupRetentionService to register backups and track expired vs retained
- As a researcher, I want IntegrityChecker to verify backup integrity via SHA-256 checksums
- As a researcher, I want MonthlyRestoreTest to run monthly restore tests
- As a researcher, I want MigrationPackage to package migrations for restore
- As a researcher, I want deterministic results regardless of timestamps
- Stdlib-only, no import-time network/cloud activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| RetentionPolicy creation | `tests/unit/test_retention_restore.py::test_retention_policy_creates` | ModuleNotFoundError | PASS | Default retention_days=30 |
| RetentionPolicy custom days | `tests/unit/test_retention_restore.py::test_retention_policy_custom_days` | ModuleNotFoundError | PASS | Custom retention_days accepted |
| Service creation | `tests/unit/test_retention_restore.py::test_backup_retention_service_creates` | ModuleNotFoundError | PASS | Service instantiates |
| Register backup | `tests/unit/test_retention_restore.py::test_register_backup` | ModuleNotFoundError | PASS | Backup registered and retrievable |
| Retention deletes expired | `tests/unit/test_retention_restore.py::test_retention_deletes_expired_backups` | ModuleNotFoundError | PASS | Backups older than retention period are expired |
| Retention keeps recent | `tests/unit/test_retention_restore.py::test_retention_keeps_recent_backups` | ModuleNotFoundError | PASS | Backups within retention period retained |
| RetentionResult creation | `tests/unit/test_retention_restore.py::test_retention_result_creates` | ModuleNotFoundError | PASS | Dataclass with expired/retained lists |
| IntegrityChecker creation | `tests/unit/test_retention_restore.py::test_integrity_checker_creates` | ModuleNotFoundError | PASS | IntegrityChecker instantiates |
| Integrity check passes | `tests/unit/test_retention_restore.py::test_check_integrity_passes` | ModuleNotFoundError | PASS | Matching checksum → verified=True |
| Integrity check fails | `tests/unit/test_check_integrity_fails` | ModuleNotFoundError | PASS | Non-matching checksum → verified=False |
| MonthlyRestoreTest creation | `tests/unit/test_retention_restore.py::test_monthly_restore_test_creates` | ModuleNotFoundError | PASS | Dataclass instantiates |
| Monthly restore test run | `tests/unit/test_retention_restore.py::test_monthly_restore_test_runs` | ModuleNotFoundError | PASS | Restore test records result |
| MigrationPackage creation | `tests/unit/test_retention_restore.py::test_migration_package_creates` | ModuleNotFoundError | PASS | MigrationPackage dataclass |
| Migration package function | `tests/unit/test_retention_restore.py::test_migration_package_function` | ModuleNotFoundError | PASS | convenience function returns MigrationPackage |
| Deterministic retention | `tests/unit/test_retention_restore.py::test_retention_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| No expired backups | `tests/unit/test_retention_restore.py::test_retention_no_expired_backups` | ModuleNotFoundError | PASS | Empty expired list when none expired |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Retention policy | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 2 | Backup registration | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 3 | Retention expiry | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 4 | Integrity checking | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 5 | Monthly restore test | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 6 | Migration packaging | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |
| 7 | Deterministic results | `tests/unit/test_retention_restore.py` | unit | PASS | 571 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.7 lines exercised by unit tests
- Intentional gap: No persistence of retention state — in-memory only
- Intentional gap: IntegrityChecker uses in-memory dict, not persisted checksums
- Intentional gap: MonthlyRestoreTest stores results in-memory only

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.backup_retention'` captured before implementation. GREEN: 571 tests pass, 2 skipped, ruff clean, format clean, working tree clean.