# TDD Evidence Report — Phase 4.2: Distinguish synthetic fixtures from live observations

**Task:** V1 Stabilization and Security Repair Sprint — Phase 4.2
**Branch:** `repair/v1-stabilization`
**Date:** Sat Oct 31 2026

---

## Source plan

Evaluation report: `docs/EVALUATION-REPORT-V1-STABILIZATION.md`
- D-7: Synthetic fixtures presented as live data throughout the UI

## User journeys

- As a system operator, I want every dashboard surface to explicitly label whether its data is synthetic fixture, imported history, or probed from a live service, so I can distinguish synthetic from real data
- As a system operator, I want no surface to imply any data is live broker data, so I never mistake simulated values for real market data
- As a system operator, I want the data explorer chart annotations to state the source and "not live broker data", so chart viewers understand data provenance
- As a system operator, I want the research queue, strategy workbench, validation experiments, audit library, and settings surfaces to label their data source, so all surfaces consistently distinguish synthetic from live

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Overview shows NOT_PROBED health states | `tests/unit/test_m11_ui.py::test_render_overview_shows_data_provenance` | AssertionError | PASS | Overview labels health components as "not probed" |
| Research queue labels data as synthetic | `tests/unit/test_m11_ui.py::test_render_research_queue_shows_data_provenance` | AssertionError | PASS | Research queue calls `source_label("synthetic_fixture")` |
| Strategy workbench shows proposal source | `tests/unit/test_m11_ui.py::test_render_strategy_workbench_shows_proposal_source` | AssertionError | PASS | Workbench displays "source" (deterministic/AI) |
| Validation experiments show data source | `tests/unit/test_m11_ui.py::test_render_validation_experiments_shows_data_source` | AssertionError | PASS | Experiments show experiment data |
| Audit library shows data source | `tests/unit/test_m11_ui.py::test_render_audit_library_shows_data_source` | AssertionError | PASS | Audit library calls `source_label("synthetic_fixture")` |
| Settings profiles show config source | `tests/unit/test_m11_ui.py::test_render_settings_profiles_shows_config_source` | AssertionError | PASS | Settings displays "source" field |
| No surface implies live broker data | `tests/unit/test_m11_ui.py::test_no_surface_implies_live_broker_data` | AssertionError | PASS | All surfaces state "not live"/"internal simulation"/"synthetic" |
| Chart annotations state source | `tests/unit/test_m11_ui.py::test_chart_annotations_state_source` | AssertionError | PASS | Chart annotations include "synthetic" |
| Chart annotations state not-live | `tests/unit/test_m11_ui.py::test_chart_annotations_state_not_live` | AssertionError | PASS | Chart annotations include "not live" |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Overview labels health as not probed | `tests/unit/test_m11_ui.py::test_render_overview_shows_data_provenance` | unit | PASS | 1 test passes |
| 2 | Research queue labels data synthetic | `tests/unit/test_m11_ui.py::test_render_research_queue_shows_data_provenance` | unit | PASS | 1 test passes |
| 3 | Strategy workbench shows proposal source | `tests/unit/test_m11_ui.py::test_render_strategy_workbench_shows_proposal_source` | unit | PASS | 1 test passes |
| 4 | Validation experiments show data source | `tests/unit/test_m11_ui.py::test_render_validation_experiments_shows_data_source` | unit | PASS | 1 test passes |
| 5 | Audit library shows data source | `tests/unit/test_m11_ui.py::test_render_audit_library_shows_data_source` | unit | PASS | 1 test passes |
| 6 | Settings profiles show config source | `tests/unit/test_m11_ui.py::test_render_settings_profiles_shows_config_source` | unit | PASS | 1 test passes |
| 7 | No surface implies live broker data | `tests/unit/test_m11_ui.py::test_no_surface_implies_live_broker_data` | unit | PASS | 1 test passes |
| 8 | Chart annotations state source | `tests/unit/test_m11_ui.py::test_chart_annotations_state_source` | unit | PASS | 1 test passes |
| 9 | Chart annotations state not-live | `tests/unit/test_m11_ui.py::test_chart_annotations_state_not_live` | unit | PASS | 1 test passes |

## Coverage and known gaps

- All 8 dashboard surfaces now explicitly label data as synthetic/internal simulation:
  - Overview: health components start as NOT_PROBED, coverage text says "Unavailable/unverified mappings shown; values never fabricated"
  - Data explorer: `source_label("synthetic_fixture")` + chart annotations
  - Research queue: `source_label("synthetic_fixture")` added
  - Strategy workbench: shows `proposal_source` (deterministic/AI)
  - Validation experiments: shows experiment data with run_id/strategy_version
  - Portfolio risk: `source_label("synthetic_fixture")`
  - Audit library: `source_label("synthetic_fixture")` added
  - Settings profiles: shows `source` field (config.yaml)
- All charts use `ohlcv_chart()` with `source="synthetic_fixture"` and annotations stating "not live broker data"
- Full `tests/unit` + `tests/e2e` suite exits 0
- ruff clean on all new/changed files

## Merge evidence

RED: AssertionError on tests checking for provenance labels in UI surfaces captured before implementation. GREEN: All Phase 4.2 tests pass; full `tests/unit` + `tests/e2e` suite exits 0; ruff clean. New/changed files: `src/superbot/m11/ui.py`, `tests/unit/test_m11_ui.py`.
