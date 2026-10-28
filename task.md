# Superbot Implementation Task Ledger

**Rule:** This is the single prioritized build queue. Update it after every task and milestone. Never mark DONE without command/output evidence and specification updates. Status labels: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DEFERRED`.

## 0. Current state

- [x] Specification pack drafted from user-confirmed decisions and supplied synthetic POC evidence. This does **not** mean the application code is implemented.
- [x] User-run synthetic baseline POC: correctness PASS (7 checks), Python 3.14.7; evidence in `context.md`/`memory.md`.
- [ ] NautilusTrader/LEAN engine POCs not run on laptop.
- [ ] Reliable process-tree resource benchmark pending.
- [ ] Full app, MT5 integration, PostgreSQL integration, local model, dashboard and backup/restore not verified.

## M0 — Repository and OpenCode/ECC reconnaissance

- [x] `M0.1` Inspect repo tree, Git status/branch/commit, code and tests. Preserve existing work. — C:\SuperBot not a git repo; no existing app code/tests; spec pack present at root; nothing overwritten.
- [x] `M0.2` Inspect active OpenCode version/config, actual MCPs, skills, plugins, agents, permissions and ECC commands/version. Save evidence table. — OpenCode v2.1.2; ecc 2.2.2 plugin; context7/playwright/supabase/github plugins installed; loop-start/loop-status/quality-gate/harness-audit/security-scan/code-review commands present as files (active registration not confirmed); no .claude/commands dir.
- [x] `M0.3` Read specs; reconcile conflicts/unknowns and list OPEN decisions/blockers. — PRD/architecture/schema/rules/agents/context/task/memory/design/START_PROMPT/README/MANIFEST reviewed; conflicts none found; OPEN register in context.md section 11 confirmed.
- [x] `M0.4` Verify Python/dependency tooling and current machine state without installing unreviewed stacks. — Python 3.14.7, pip 26.2.1, pytest 9.1.1, ruff 0.17.2; psycopg/sqlalchemy OK; metatrader5 pip-installed but ModuleNotFoundError on import (BLOCKER for MT5); PostgreSQL 18 running; psql 18.0.6.0.
- [x] `M0.5` Update `context.md` with findings, repository map and ADR index. — Section 13 added with M0 findings; ADR index empty (no ADRs yet; M1.1 will create layout ADR).

**Acceptance:** repo/tool state documented; working tree preserved; no unrecorded application code changes during reconnaissance. — MET. Baseline POC re-verified PASS (context.md section 13).

## M1 — Contracts, configuration and foundation

- [x] `M1.1` Decide source/package/test layout from inspection; record ADR. — ADR-001 (docs/adr/0001-package-layout.md), src layout, pyproject.toml, pytest+ruff configured; commit 5954dc9.
- [x] `M1.2` Define versioned canonical contracts from `schema.md`. — DONE: InstrumentSpec (§2) + OHLCVBar (§3) contracts with enums, Decimal-or-null fields, validation, tests, lint, format (commits a004d15 + latest).
- [x] `M1.3` Add validated config and profiles `research`/`internal-simulation`; future `demo-readiness` remains guarded. — src/superbot/config.py (Profile enum, SuperbotConfig, InvalidConfigError); demo-readiness rejected; commit 5954dc9.
- [x] `M1.4` Structured logs/correlation IDs and secret-redaction tests. — `src/superbot/observability/logging.py` (contextvar correlation ID, JsonFormatter, CorrelationFilter, secret redaction); tests pass.
- [x] `M1.5` Supervisor/health model and controlled startup/shutdown skeleton. — `src/superbot/supervisor/health.py` (HealthStatus enum, HealthCheckResult, HealthRegistry with register/run_all/overall); tests pass.
- [x] `M1.6` Establish tests, lint/type/security/format commands and CI or local equivalent. — pytest/ruff configured (pyproject.toml); `py -m pytest` passes, ruff clean.

**Acceptance:** fresh test run passes; invalid config rejected; secrets redacted; no import-time network/model/MT5 work. — MET for M1.1/M1.3 subset (4 tests pass, stdlib-only import, no secrets).

## M2 — Data contracts and quality pipeline

- [ ] `M2.1` Canonical OHLCV/instrument/provider metadata.
- [ ] `M2.2` Synthetic fixtures/tests for chronology, duplicates, gaps, staleness, suspicious data and availability timestamps.
- [ ] `M2.3` Dataset manifest/version/hash and lineage.
- [ ] `M2.4` Session/timezone boundary validation with explicit unknown state.
- [ ] `M2.5` Verify read-only MT5 adapter API/symbol/spec discovery only after local setup permits; no order access.
- [ ] `M2.6` Benchmark Parquet vs alternative history stores on representative data/laptop; ADR.

**Acceptance:** corrupt/missing/stale/unverified data blocks affected work; sources never silently merged; actual coverage recorded per symbol/timeframe.

## M3 — Engine POC and selection

- [ ] `M3.1` Extend custom baseline fixtures into event-by-event reference harness.
- [ ] `M3.2` Define equivalence fixtures, strategy rules, cost conventions and acceptance tests before candidate tests.
- [ ] `M3.2a` Freeze the standardized POC protocol: small correctness fixture + representative dataset + optional stress set; strict correctness gate; one warm-up + five measured repetitions; comprehensive metrics and reproducible evidence retention. Define any noise/additional-run rule before reviewing benchmark outcomes.
- [ ] `M3.3` POC NautilusTrader in isolated, pinned environment.
- [ ] `M3.4` POC QuantConnect LEAN in isolated, pinned environment; test local self-managed workflow without hosted inference/platform dependency.
- [ ] `M3.5` Assess alternative engine only for a demonstrated capability gap.
- [ ] `M3.6` Correctness first, then runtime, process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, repeatability, failure rate and critical-service impact.
- [ ] `M3.7` Score using weights below, only from comparable evidence.
- [ ] `M3.8` Select engine/combination via ADR; winner >=80/100, every mandatory gate passed and no unresolved critical integration risk.

Weights: safety/correctness 30%; compatibility 20%; reproducibility 15%; resource efficiency 15%; maintainability 10%; performance 10%. Hard disqualifiers: mandatory correctness failure, inability to enforce Superbot deterministic risk, unresolved critical security issue or unacceptable terms/licence. User says existing candidate license review is clear; continue recording actual adopted versions.

**Acceptance:** same inputs/rules/costs/splits, pinned versions and isolated environments; no scores from popularity or tiny microbenchmark. If laptop cannot support a candidate, record blocker honestly.

## M4 — Deterministic simulator and accounting

- [ ] `M4.1` Next-bar-open market fill semantics.
- [ ] `M4.2` Same-bar SL/TP stop-first and adverse stop-gap logic.
- [ ] `M4.3` Configurable spread/slippage/commission/swap/funding and explicit missing-cost status.
- [ ] `M4.4` Limit trade-through policy/event sequencing.
- [ ] `M4.5` Verified tick/contract/volume constraints; block if missing/stale.
- [ ] `M4.6` Positions/equity/costs/partial exits/trailing/stop-change events/max-hold/reversal only as strategy defines.
- [ ] `M4.7` Differential/property tests and deterministic replay.

**Acceptance:** money/event accounting tests pass; no future-data access; ambiguous OHLCV events conservative; all simulated events/rejections traceable.

## M5 — Strategies, signals and lifecycle

- [ ] `M5.1` Versioned rule schema, stable IDs, dedup/expiry/invalidation/reversal.
- [ ] `M5.2` Trend-following/pullback definition and tests.
- [ ] `M5.3` Liquidity-sweep/structure strategy; precise BOS/CHOCH definitions; defer OB/FVG until precise rule acceptance.
- [ ] `M5.4` Explicit quantitative/statistical baseline and tests.
- [ ] `M5.5` Shared framework and versioned configs; no ten LLM strategy agents.
- [ ] `M5.6` Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests.

**Acceptance:** strategy rules explicit/versioned/deterministic; no discretionary term without operational definition.

## M6 — Validation and promotion gates

- [ ] `M6.1` Chronological train/validation/untouched-test split and leakage audit.
- [ ] `M6.2` >=3 walk-forward windows and metric-accounting tests.
- [ ] `M6.3` PF/Sharpe/Sortino/DD/trade-count gates with documented conventions.
- [ ] `M6.4` Parameter-neighbor robustness and quantitative stable-region definition (requires OPEN decision closure).
- [ ] `M6.5` Trial counting, baselines/no-trade comparison and multiple-testing controls.
- [ ] `M6.6` Cost-adjusted OOS and 2x-cost stress; disclose missing costs.
- [ ] `M6.7` Shadow mode with configurable opportunity count, elapsed time and data-quality conditions.
- [ ] `M6.8` Internal-simulation eligibility and three-failed-validation-attempt version archive rule.

**Acceptance:** leaks/unrobust candidates cannot pass; untouched test isolation reproducible; no model can set PASS directly.

## M7 — Portfolio/risk/resource manager

- [ ] `M7.1` Portfolio/strategy/correlation-group risk service.
- [ ] `M7.2` Daily loss 3% and portfolio DD 10% halt/resume process.
- [ ] `M7.3` Combined open-risk cap 5%; adaptive risk and verified sizing.
- [ ] `M7.4` Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase; numeric tier criteria remain OPEN.
- [ ] `M7.5` ATR-relative volatility and hard blocks; thresholds OPEN, never guessed.
- [ ] `M7.6` Competing signal ranking, reserve/capacity, group limits, resize/reject semantics.
- [ ] `M7.7` Boundaries/concurrency/missing-input tests and risk audit events.

**Acceptance:** all gates pass; unverifiable inputs block entries; AI cannot override; breaches pause new entries while existing simulated positions continue under defined exits.

## M8 — Persistence, audit and recovery

- [ ] `M8.1` PostgreSQL config/suitability benchmark on laptop.
- [ ] `M8.2` Versioned migrations and old experiment readability.
- [ ] `M8.3` Append-only audit and correction linkage.
- [ ] `M8.4` Experiment registry/data-code-strategy-parameter-cost-config refs.
- [ ] `M8.5` Checkpoint/crash restart reconciliation for jobs/signals/positions.
- [ ] `M8.6` Local + encrypted cloud backup; decide provider/key management with ADR; exclude secrets.
- [ ] `M8.7` 30-day retention, integrity checks, monthly restore test and migration package.

**Acceptance:** recovery and restore tested; audit integrity failure blocks promotion; no silent evidence deletion; secrets excluded.

## M9 — Local AI and runtime agents

- [ ] `M9.1` Benchmark Ollama vs llama.cpp on laptop/desktop using task fixtures.
- [ ] `M9.2` Qualify task/model routes on quality, schema, repeatability, latency, memory.
- [ ] `M9.3` Implement agent contracts/permissions/proposal store/deterministic orchestration.
- [ ] `M9.4` Analyst, strategy proposer, reviewer and diagnostic/improvement roles.
- [ ] `M9.5` Timeout/retry/fallback/skip/conflict and resource-routing tests.
- [ ] `M9.6` News/sentiment only after core technical pipeline is reliable; permitted free sources.
- [ ] `M9.7` Prompt injection, untrusted text and malformed output tests.

**Acceptance:** no hosted inference; no suitable model means dependent work marked incomplete; no AI writes official state.

## M10 — Scheduler/supervisor/operations

- [ ] `M10.1` Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules.
- [ ] `M10.2` Resource telemetry for API/workers/DB/model/MT5/data/queue.
- [ ] `M10.3` Graceful shutdown/checkpoint, restart checks and resume guard.
- [ ] `M10.4` Alerts, operator actions and audit traces.

**Acceptance:** resource pressure does not starve integrity/risk/position management; recovery failures remain blocked.

## M11 — Dashboard/UX

- [ ] `M11.1` Select UI/API/chart stack using inspection + ADR.
- [ ] `M11.2` Overview, data explorer, jobs, strategy/signals, validation, portfolio/risk, audit/experiments, settings/profiles.
- [ ] `M11.3` Auth sessions/roles/redaction/local binding/private VPN docs.
- [ ] `M11.4` Browser tests, empty/loading/error states, accessibility and actual screenshot evidence.

**Acceptance:** backend-driven state, explicit synthetic/source labels, no fake success or live-order controls, no public exposure.

## M12 — Release hardening and migration

- [ ] `M12.1` Unit/integration/e2e/data/simulator/risk/security/recovery/audit/backup/restore suites.
- [ ] `M12.2` Full regression for changes, static/dependency/security scan.
- [ ] `M12.3` Local install/run docs and known-good configuration.
- [ ] `M12.4` Laptop-to-desktop migration/revalidation.
- [ ] `M12.5` Release review, explicit human approval and doc updates.

**Acceptance:** no critical/high unresolved defect; all mandatory gates passed and evidence preserved; human approval. No live trading.

## Task entry template

```markdown
### T-XXX — [short title]
- Status: NOT_STARTED | IN_PROGRESS | BLOCKED | DONE | DEFERRED
- Dependencies:
- Scope (in/out):
- Acceptance criteria:
- Tests/commands:
- Evidence / commit:
- Spec files to update:
- Risks / rollback:
- Blocker / reason:
```

## Milestone closure checklist

- [ ] Acceptance criteria met with evidence.
- [ ] Focused/regression tests run; skipped checks listed.
- [ ] ECC/review/quality gate run if available, or manual review documented.
- [ ] `git diff --check` and final diff review completed.
- [ ] Relevant specs/memory/context and `task.md` updated.
- [ ] No unresolved critical/high issue or hidden blocker.
- [ ] Next smallest task selected; no scope ballooning.
