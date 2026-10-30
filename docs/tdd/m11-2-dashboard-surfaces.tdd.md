# TDD Evidence Report — M11.2 Dashboard surfaces (overview/data explorer/jobs/strategy-signals/validation/portfolio-risk/audit-experiments/settings-profiles)

## Source plan

No `*.plan.md` provided; user journeys derived during this TDD run from `task.md` `M11.2` ("Overview, data explorer, jobs, strategy/signals, validation, portfolio/risk, audit/experiments, settings/profiles") and `design.md` §2 primary surfaces, plus `architecture.md` §8/§11 (audit records every decision; dashboard shows state/blockers).

## User journeys

- As a system operator, I want an overview health row (API, PostgreSQL, worker supervisor, model runtime, MT5 read-only status, last update, data freshness, backup state) so I can see system state at a glance
- As a system operator, I want instrument/timeframe coverage (Gold, Silver, Bitcoin, Ethereum, US Oil × M5/M15/H1/H4) showing unavailable/unverified mappings, never fabricated values
- As a researcher, I want an OHLCV chart labeled by provider/source, symbol mapping, timeframe, timestamp convention, freshness and coverage, with data-quality state and never-implied-live labels
- As a researcher, I want research queue jobs with status, dataset/symbol/timeframe, strategy/config version, priority, resource use, progress/checkpoint, start/duration and pause/resume/cancel, with duplicate-overlap prevention and destructive-cancel confirmation
- As a strategist, I want strategy family/version/parameters, machine-readable rules, proposal source (deterministic vs AI), evidence refs, schema validation outcome, signal ID, and deterministic rejection reason — AI suggestions never presented as approved trades
- As a validator, I want experiment gate states PASS/FAIL/BLOCKED/NOT RUN with timestamp/config/evidence, and failed experiments remaining searchable
- As a risk officer, I want simulated positions/P&L/exposure, limits, drawdown peak, halt state, with missing/stale specs showing blocked never zero-risk/green, labeled internal simulation
- As an auditor, I want append-only audit events (run ID, strategy/version, symbol/timeframe, date, data hash, outcome, gate, failure class, commit), evidence refs, correction linkage, chain integrity
- As an owner, I want settings/profiles (research, internal-simulation, guarded demo-readiness) with value/range/source/version/actor/reason/timestamp/last-known-good, secrets redacted, no live-order control, owner-only changes

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Health endpoint all components | `tests/unit/test_m11_api.py::test_health_returns_all_components` | ModuleNotFoundError | PASS | API, PostgreSQL, worker supervisor, model runtime, MT5 read-only status, last update, data freshness, backup state |
| Health overall reflects worst component | `tests/unit/test_m11_api.py::test_health_overall_reflects_worst_component` | ModuleNotFoundError | PASS | Overall = blocked/degraded/healthy per worst component |
| Data explorer source + not-live label | `tests/unit/test_m11_api.py::test_data_explorer_labels_source_and_not_live` | ModuleNotFoundError | PASS | Source ∈ {synthetic_fixture, imported_history, broker_feed}, live=false |
| Jobs lifecycle fields | `tests/unit/test_m11_api.py::test_jobs_returns_status_and_lifecycle_fields` | ModuleNotFoundError | PASS | All job fields present (status, dataset, symbol, timeframe, versions, priority, resource, progress, checkpoint, duration, pause/resume/cancel) |
| Duplicate overlap prevention | `tests/unit/test_m11_api.py::test_jobs_prevents_duplicate_overlaps` | ModuleNotFoundError | PASS | duplicate_checks returned for duplicate dataset/symbol/timeframe |
| Destructive cancel confirmation | `tests/unit/test_m11_api.py::test_job_cancel_requires_confirmation_when_uncheckpointed` | ModuleNotFoundError | PASS | Uncheckpointed cancel returns 400 blocked with reason |
| Strategy lifecycle + rejection reason | `tests/unit/test_m11_api.py::test_strategies_return_lifecycle_and_rejection_reason` | ModuleNotFoundError | PASS | Lifecycle ∈ {proposed,blocked,validating,shadow,internal_simulation,archived}; rejection_reason present when rejected |
| AI suggestion never approved | `tests/unit/test_m11_api.py::test_ai_suggestion_never_presented_as_approved` | ModuleNotFoundError | PASS | AI-proposed strategy lifecycle != approved; rejection_reason set |
| Experiment gate states | `tests/unit/test_m11_api.py::test_experiments_gate_states_distinguished` | ModuleNotFoundError | PASS | Gate state ∈ {PASS,FAIL,BLOCKED,NOT RUN} with timestamp/config/evidence |
| Failed experiments searchable | `tests/unit/test_m11_api.py::test_failed_experiments_remain_searchable` | ModuleNotFoundError | PASS | outcome=failed filter returns experiments |
| Risk positions + limits | `tests/unit/test_m11_api.py::test_risk_returns_positions_and_limits` | ModuleNotFoundError | PASS | positions, exposure, pnl, daily_loss_usage, drawdown_peak, halt_state, label=internal_simulation |
| Missing/stale specs blocked | `tests/unit/test_m11_api.py::test_missing_stale_specs_show_blocked_not_zero_risk` | ModuleNotFoundError | PASS | blocked=true, risk_state != green, reason present |
| Audit events with refs | `tests/unit/test_m11_api.py::test_audit_returns_append_only_events_with_refs` | ModuleNotFoundError | PASS | All audit fields present (run_id, strategy_version, symbol, timeframe, date, data_hash, outcome, gate, failure_class, commit) |
| Audit chain integrity | `tests/unit/test_m11_api.py::test_audit_chain_integrity` | ModuleNotFoundError | PASS | chain_intact=true |
| Settings profiles metadata | `tests/unit/test_m11_api.py::test_settings_returns_profiles_with_metadata` | ModuleNotFoundError | PASS | research/internal_simulation/demo_readiness with value/range/source/version/actor/reason/timestamp/last_known_good |
| Secrets redacted | `tests/unit/test_m11_api.py::test_settings_secrets_redacted_and_nonexportable` | ModuleNotFoundError | PASS | secret_redacted=true |
| No live-order control | `tests/unit/test_m11_api.py::test_settings_no_live_order_control` | ModuleNotFoundError | PASS | live_orders_enabled=false |
| Owner-only settings change | `tests/unit/test_m11_api.py::test_settings_only_authorized_owner_can_change` | ModuleNotFoundError | PASS | Non-owner settings change returns 403 |
| No public exposure | `tests/unit/test_m11_api.py::test_api_bind_localhost_only` | ModuleNotFoundError | PASS | OpenAPI servers are localhost-only, no 0.0.0.0/public |
| Plotly OHLCV figure | `tests/unit/test_m11_charts.py::test_ohlcv_chart_returns_plotly_figure` | ModuleNotFoundError | PASS | Returns go.Figure with candlestick + volume traces |
| Chart source/not-live annotations | `tests/unit/test_m11_charts.py::test_ohlcv_chart_labels_source_and_not_live` | ModuleNotFoundError | PASS | Annotations state source + "not live broker data" |
| Overlay labeled by definition/version | `tests/unit/test_m11_charts.py::test_overlay_line_labeled_by_definition_version` | ModuleNotFoundError | PASS | legendgroup = "{definition} {version}", hovertemplate includes definition |
| Chart includes overlays | `tests/unit/test_m11_charts.py::test_ohlcv_chart_includes_overlays` | ModuleNotFoundError | PASS | Overlay traces present in figure |
| Chart title symbol+timeframe | `tests/unit/test_m11_charts.py::test_ohlcv_chart_timeframe_and_symbol_in_title` | ModuleNotFoundError | PASS | Title includes symbol and timeframe |
| Health/gate/source format helpers | `tests/unit/test_m11_ui.py::test_health_badge_maps_status`, `test_gate_badge_distinguishes_states`, `test_format_pct_precise_units`, `test_source_label_not_live` | ModuleNotFoundError | PASS | Badges map status to text+icon (color not only signal), pct formatted, source labels not live |
| All 8 surface renderers exist | `tests/unit/test_m11_ui.py::test_all_surface_renderers_exist` | ModuleNotFoundError | PASS | render_overview, render_data_explorer, render_research_queue, render_strategy_workbench, render_validation_experiments, render_portfolio_risk, render_audit_library, render_settings_profiles |
| Surface smoke tests | `tests/unit/test_m11_ui.py` render_* | ModuleNotFoundError | PASS | Each renderer calls UI with backend-driven state; no live-order control button |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | FastAPI backend-driven state for all 8 surfaces | `tests/unit/test_m11_api.py` | unit | PASS | 19 tests pass |
| 2 | Health row + overall status | `tests/unit/test_m11_api.py::test_health_*` | unit | PASS | 2 tests pass |
| 3 | Data explorer source/not-live labels | `tests/unit/test_m11_api.py::test_data_explorer_labels_source_and_not_live` | unit | PASS | live=false |
| 4 | Research queue jobs + duplicate prevention + cancel confirmation | `tests/unit/test_m11_api.py::test_jobs_*` | unit | PASS | 3 tests pass |
| 5 | Strategy lifecycle + rejection reason + no AI-as-approved | `tests/unit/test_m11_api.py::test_strategies_*` | unit | PASS | 2 tests pass |
| 6 | Experiment gate states PASS/FAIL/BLOCKED/NOT RUN + failed searchable | `tests/unit/test_m11_api.py::test_experiments_*` | unit | PASS | 2 tests pass |
| 7 | Portfolio/risk internal simulation + blocked-not-zero-risk | `tests/unit/test_m11_api.py::test_risk_*` | unit | PASS | 2 tests pass |
| 8 | Audit events + chain integrity | `tests/unit/test_m11_api.py::test_audit_*` | unit | PASS | 2 tests pass |
| 9 | Settings profiles + secrets redacted + no live order + owner-only | `tests/unit/test_m11_api.py::test_settings_*` | unit | PASS | 4 tests pass |
| 10 | No public exposure (localhost only) | `tests/unit/test_m11_api.py::test_api_bind_localhost_only` | unit | PASS | OpenAPI servers localhost-only |
| 11 | Plotly OHLCV chart + overlays + annotations | `tests/unit/test_m11_charts.py` | unit | PASS | 5 tests pass |
| 12 | UI pure helpers (badges, pct, source labels) | `tests/unit/test_m11_ui.py::test_*_badge|format_pct|source_label` | unit | PASS | 4 tests pass |
| 13 | All 8 UI surfaces render backend-driven state | `tests/unit/test_m11_ui.py::test_render_* + test_all_surface_renderers_exist` | unit | PASS | 9 tests pass |

## Coverage and known gaps

- No coverage tool configured; all `superbot.m11.api`, `superbot.m11.charts`, `superbot.m11.ui` lines exercised by unit tests (every endpoint, helper, chart function, and render function is called).
- Full `tests/unit` suite exits 0 (some MT5-terminal-dependent tests skipped when no live MT5 is available).
- ruff clean (line-length 100); no import-time network/database/MT5 activity in M11 modules.
- Intentional gap: actual Streamlit browser rendering and screenshot evidence deferred to M11.4 (browser tests, empty/loading/error states, accessibility). M11.2 render functions are dependency-injected and smoke-tested against a fake UI object.
- Intentional gap: persistent job/strategy/experiment/audit state is in-memory deterministic fixtures for M11.2; PostgreSQL persistence wiring happens via existing persistence modules (audit_linkage, experiment_registry) and is exercised at lower levels.
- No live orders in V1; all values labeled `internal_simulation` / `synthetic_fixture`; no public network binding.

## Merge evidence

RED: `ModuleNotFoundError: No module named 'superbot.m11.api'` (and `.charts`, `.ui`) captured before implementation. GREEN: 37 M11.2 tests pass; full `tests/unit` suite exits 0; ruff clean. New files: `src/superbot/m11/api.py`, `src/superbot/m11/charts.py`, `src/superbot/m11/ui.py`; tests: `tests/unit/test_m11_api.py`, `tests/unit/test_m11_charts.py`, `tests/unit/test_m11_ui.py`. `plotly` added to runtime dependencies (installed 7.1.0); `pyproject.toml` dependencies updated accordingly.
