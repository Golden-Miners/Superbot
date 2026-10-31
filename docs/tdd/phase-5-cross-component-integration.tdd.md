# TDD Evidence Report — Phase 5: Cross-component integration

**Task:** V1 Stabilization and Security Repair Sprint — Phase 5
**Branch:** `repair/v1-stabilization`
**Date:** Sat Oct 31 2026

---

## Source plan

Evaluation report: `docs/EVALUATION-REPORT-V1-STABILIZATION.md`
- D-6: Seeded healthy service states → real probes
- D-7: Synthetic vs live source labels throughout UI
- D-8: Real job-state transitions and cancellation API
- M11.2: Connect dashboard surfaces to backend services
- M11.3: Integrate risk services with internal simulator

## User journeys

- As a system operator, I want the dashboard health row to reflect actual health check results (not hardcoded values), so I can trust the system status
- As a system operator, I want the portfolio/risk surface to reflect real risk calculations from the risk service, so I can trust risk assessments
- As a system operator, I want the audit/experiment library to show real audit events from the append-only audit log, so I can verify decision integrity
- As a system operator, I want the research queue to show real jobs from the scheduler, so I can track research progress
- As a system operator, I want strategy/workbench data to come from the strategy framework, so I see actual strategy configurations
- As a system operator, I want validation/experiment data from the experiment registry, so I see real experiment results
- As a system operator, I want risk service integrated with the internal simulator, so risk limits reflect actual simulation outcomes
- As a system operator, I want versioned PostgreSQL migrations to work, so schema evolution is tracked
- As a system operator, I want checkpoint/restart to work, so crash recovery is possible
- As a system operator, I want all dashboard values labeled as internal_simulation/synthetic_fixture, so I never confuse simulated data with live broker data

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Health reads from HealthRegistry | `tests/unit/test_m11_integration.py::test_health_reads_from_health_registry` | ImportError | PASS | Health endpoint returns actual check results |
| Risk reads from PortfolioRiskService | `tests/unit/test_m11_integration.py::test_risk_reads_from_portfolio_risk_service` | ImportError | PASS | Risk endpoint returns real risk data |
| Audit events from AuditEventLogger | `tests/unit/test_m11_integration.py::test_audit_events_read_from_audit_logger` | ImportError | PASS | Audit endpoint returns real events |
| Experiments from ExperimentRegistry | `tests/unit/test_m11_integration.py::test_experiments_read_from_experiment_registry` | ImportError | PASS | Experiments endpoint returns real experiments |
| Jobs from Scheduler | `tests/unit/test_m11_integration.py::test_jobs_read_from_scheduler` | ImportError | PASS | Jobs endpoint returns real jobs |
| Strategies from strategy modules | `tests/unit/test_m11_integration.py::test_strategies_read_from_strategy_modules` | ImportError | PASS | Strategies endpoint returns real strategies |
| Risk integrates with simulator | `tests/unit/test_m11_integration.py::test_risk_integrates_with_internal_simulator` | ImportError | PASS | Risk service reflects simulator results |
| MigrationService applies migrations | `tests/unit/test_m11_integration.py::test_migration_service_applies_and_tracks` | ImportError | PASS | Migrations applied once, tracked |
| MigrationService prevents double-apply | `tests/unit/test_m11_integration.py::test_migration_service_prevents_double_apply` | ImportError | PASS | Migrations applied at most once |
| CheckpointService saves/restores | `tests/unit/test_m11_integration.py::test_checkpoint_service_saves_and_restores` | ImportError | PASS | Checkpoints persist and restore |
| FastAPI health uses DashboardService | `tests/unit/test_m11_integration.py::test_fastapi_health_endpoint_uses_dashboard_service` | ImportError | PASS | API endpoint uses service layer |
| All surfaces labeled internal_simulation | `tests/unit/test_m11_integration.py::test_all_surfaces_labeled_internal_simulation` | ImportError | PASS | All surfaces labeled internal_simulation |
| No broker credentials exposed | `tests/unit/test_m11_integration.py::test_no_broker_credentials_in_dashboard` | ImportError | PASS | No credentials in any surface |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Health endpoint reads from HealthRegistry | `tests/unit/test_m11_integration.py::test_health_reads_from_health_registry` | unit | PASS | 1 test passes |
| 2 | Risk endpoint reads from PortfolioRiskService | `tests/unit/test_m11_integration.py::test_risk_reads_from_portfolio_risk_service` | unit | PASS | 1 test passes |
| 3 | Audit endpoint reads from AuditEventLogger | `tests/unit/test_m11_integration.py::test_audit_events_read_from_audit_logger` | unit | PASS | 1 test passes |
| 4 | Experiments endpoint reads from ExperimentRegistry | `tests/unit/test_m11_integration.py::test_experiments_read_from_experiment_registry` | unit | PASS | 1 test passes |
| 5 | Jobs endpoint reads from Scheduler | `tests/unit/test_m11_integration.py::test_jobs_read_from_scheduler` | unit | PASS | 1 test passes |
| 6 | Strategies endpoint reads from strategy modules | `tests/unit/test_m11_integration.py::test_strategies_read_from_strategy_modules` | unit | PASS | 1 test passes |
| 7 | Risk integrates with internal simulator | `tests/unit/test_m11_integration.py::test_risk_integrates_with_internal_simulator` | unit | PASS | 1 test passes |
| 8 | MigrationService applies and tracks migrations | `tests/unit/test_m11_integration.py::test_migration_service_applies_and_tracks` | unit | PASS | 1 test passes |
| 9 | MigrationService prevents double-apply | `tests/unit/test_m11_integration.py::test_migration_service_prevents_double_apply` | unit | PASS | 1 test passes |
| 10 | CheckpointService saves/restores state | `tests/unit/test_m11_integration.py::test_checkpoint_service_saves_and_restores` | unit | PASS | 1 test passes |
| 11 | FastAPI /health uses DashboardService | `tests/unit/test_m11_integration.py::test_fastapi_health_endpoint_uses_dashboard_service` | integration | PASS | 1 test passes |
| 12 | All surfaces labeled internal_simulation | `tests/unit/test_m11_integration.py::test_all_surfaces_labeled_internal_simulation` | unit | PASS | 1 test passes |
| 13 | No broker credentials in dashboard | `tests/unit/test_m11_integration.py::test_no_broker_credentials_in_dashboard` | unit | PASS | 1 test passes |

## Coverage and known gaps

- New files: `src/superbot/m11/integration.py` (DashboardService), `tests/unit/test_m11_integration.py` (23 tests)
- Modified files: `src/superbot/m11/api.py` (uses DashboardService instead of in-memory STATE), `tests/unit/test_m11_api.py` (updated for new API surface)
- All 23 new tests pass; full `tests/unit` + `tests/e2e` suite exits 0
- ruff clean on all new/changed files
- `DashboardService` wraps all backend services: HealthRegistry, PortfolioRiskService, AuditEventLogger, ExperimentRegistry, Scheduler, SharedStrategyFramework, InternalSimulationEvaluator, MigrationService, CheckpointService
- All dashboard values labeled `internal_simulation` / `synthetic_fixture` — never live broker data
- No broker credentials exposed in any API response
- Known gap: Persistence is in-memory (MigrationService, CheckpointService, AuditEventLogger, ExperimentRegistry are all in-memory implementations). PostgreSQL persistence is not yet wired — this requires a database driver which is not yet in the project dependencies.
- Known gap: Background-worker lifecycle is wired through the Scheduler but no actual worker processes jobs — the scheduler manages job state but doesn't execute jobs

## Merge evidence

RED: `ModuleNotFoundError: No module named 'superbot.m11.integration'` captured before implementation. GREEN: 23 new M11.2 integration tests pass; full `tests/unit` + `tests/e2e` suite exits 0; ruff clean. New files: `src/superbot/m11/integration.py`, `tests/unit/test_m11_integration.py`. Modified files: `src/superbot/m11/api.py`, `tests/unit/test_m11_api.py`.
