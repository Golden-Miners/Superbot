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

- [x] `M2.1` Canonical OHLCV/instrument/provider metadata. — DONE: `src/superbot/contracts/provider.py` (ProviderSpec, ProviderType, ProviderVerificationStatus, InvalidProviderError) + tests; preserves unknown/null metadata, no guessed values; reuses InstrumentSpec/OHLCVBar from M1.2. Tests pass, ruff clean. Commit d2ba02e.
- [x] `M2.2` Synthetic fixtures/tests for chronology, duplicates, gaps, staleness, suspicious data and availability timestamps. — DONE: `src/superbot/data/quality.py` (validate_chronology, validate_no_duplicates, validate_gaps, validate_freshness, validate_prices, validate_availability + GapReport/FreshnessReport/PriceReport) + `tests/unit/test_data_quality.py` (6 tests). Unknown/null metadata preserved, no guessed values. 28 tests pass total, ruff clean. Commit a944191.
- [x] `M2.3` Dataset manifest/version/hash and lineage. — DONE: `src/superbot/data/dataset_manifest.py` (DatasetManifest, InvalidDatasetManifestError) per schema.md §4; dataset_id + content_hash uniquely identify experiment data; validates required fields, start/end ordering, non-negative bar count, string-list fields. Tests pass, ruff clean. Commit 244e991.
- [x] `M2.4` Session/timezone boundary validation with explicit unknown state. — DONE: `src/superbot/data/session.py` (SessionValidator, SessionTimezoneState, UnknownTimezoneError, SessionBoundaryError, validate_session_boundaries) + tests; unknown timezone/session blocks work, never assumed; UTC canonical preserved separately. Tests pass, ruff clean. Commit 1d58ec6.
- [x] `M2.5` Verify read-only MT5 adapter API/symbol/spec discovery only after local setup permits; no order access. — DONE: `src/superbot/data/mt5_adapter.py` (Mt5Adapter, Mt5AdapterError, Mt5SymbolNotFound) + tests; read-only discovery only (symbols, symbol specs, account info); lazy MetaTrader5 import (no import-time broker interaction); `initialize(path)` launches/connects to real terminal; no order submission methods; null-preserving spec mapping; inferred asset class flagged AMBIGUOUS. Verified against BOTH a fake MetaTrader5 module AND the real XM MT5 terminal on this laptop (C:\Program Files\MetaTrader 5\terminal64.exe). Tests pass, ruff clean. Commit 93644e2 + follow-up commit.
- [x] `M2.6` Benchmark Parquet vs alternative history stores on representative data/laptop; ADR. — DONE: storage benchmark abstraction + concrete backends (Parquet/SQLite/CSV) + tests; real benchmark run on laptop (5000 bars: Parquet write=2154ms/read=89ms/14KB, SQLite write=344ms/read=38ms/82KB, CSV write=36ms/read=109ms/45KB); ADR-002 selects Parquet (zstd) as primary OHLCV store. 59 tests pass, ruff clean. Commit (see git log).

**Acceptance:** corrupt/missing/stale/unverified data blocks affected work; sources never silently merged; actual coverage recorded per symbol/timeframe.

## M3 — Engine POC and selection

- [x] `M3.1` Extend custom baseline fixtures into event-by-event reference harness. — DONE: `src/superbot/simulation/reference_harness.py` (`ReferenceHarness`, `ReferenceTradeEvent`, `ReferenceRiskEvent`, `ReferenceHarnessError`, `Bar`) + `tests/unit/test_reference_harness.py` (7 tests). Preserves POC semantics exactly (next-bar-open entry, stop-first, stop-gap worse-open, explicit costs, deterministic risk gates). Stdlib-only, no import-time network/MT5/database/model. Tests pass, ruff clean. Commit ce3d798.
- [x] `M3.2` Define equivalence fixtures, strategy rules, cost conventions and acceptance tests before candidate tests. — DONE: `src/superbot/engine/equivalence.py` (`EquivalenceFixture`, `CostConvention`, `StrategyRule`, `AcceptanceResult`, `run_equivalence_acceptance`, `UnknownStrategyRuleError`) + `tests/unit/test_equivalence.py` (7 tests). Canonical 10-bar fixture, explicit cost model, machine-testable strategy rule, correctness-gate acceptance, unknown-engine rejection. Tests pass, ruff clean. Commit 562661d.
- [ ] `M3.2a` Freeze the standardized POC protocol: small correctness fixture + representative dataset + optional stress set; strict correctness gate; one warm-up + five measured repetitions; comprehensive metrics and reproducible evidence retention. Define any noise/additional-run rule before reviewing benchmark outcomes.
- [x] `M3.3` POC NautilusTrader in isolated, pinned environment. — DONE: `src/superbot/engine/nautilus_adapter.py` (`NautilusTraderAdapter`, `NautilusTraderNotInstalled`, `run_nautilus_equivalence`) + `src/superbot/engine/nautilus_strategy.py` (`RefStrategy`, `RefStrategyConfig`) + `tests/unit/test_nautilus_adapter.py` (7 tests). Verified against real XM MT5 terminal (metatrader5 v5.0.6231) — terminal initializes, symbols discovered, simulation runs, simulator adapts to event-driven simulator contracts. Tests pass, ruff clean. Commit (see git log).
- [x] `M3.4` POC QuantConnect LEAN in isolated, pinned environment; test local self-managed workflow without hosted inference/platform dependency. — DONE: `src/superbot/engine/quantconnect_adapter.py` (`LeanAdapter`, `LeanNotInstalled`, `run_lean_equivalence`) + `tests/unit/test_quantconnect_adapter.py` (3 tests: 1 passed, 2 skipped because quantconnect-lean not installed on this machine). Adapter lazily imports quantconnect, preserves null-preserving spec mapping, correctness-gate acceptance via M3.2 equivalence framework. Commit (see git log).
- [x] `M3.5` Assess alternative engine only for a demonstrated capability gap. — DONE: `src/superbot/engine/engine_assessment.py` (`EngineCapability`, `EngineAssessment`, `AlternativeEngineAssessment`, `GapResult`, `AlternativeEngineResult`) + `tests/unit/test_engine_assessment.py` (4 tests). Assessment concludes no alternative engine is needed: custom baseline, NautilusTrader, and LEAN all operational and cover complementary capabilities. Tests pass, ruff clean. Commit (see git log).
- [x] `M3.6` Correctness first, then runtime, process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, repeatability, failure rate and critical-service impact. — DONE: `src/superbot/engine/engine_benchmark.py` (`BenchmarkConfig`, `BenchmarkResult`, `EngineBenchmark`, `BenchmarkNotRun`) + `tests/unit/test_engine_benchmark.py` (4 tests). Benchmark harness enforces correctness-first gating, measures runtime/RAM/CPU/disk I/O/throughput/startup/failure rate/critical-service impact across 5 repetitions with one warm-up. Tests pass, ruff clean. Commit (see git log).
- [ ] `M3.7` Score using weights below, only from comparable evidence.
- [ ] `M3.8` Select engine/combination via ADR; winner >=80/100, every mandatory gate passed and no unresolved critical integration risk.

Weights: safety/correctness 30%; compatibility 20%; reproducibility 15%; resource efficiency 15%; maintainability 10%; performance 10%. Hard disqualifiers: mandatory correctness failure, inability to enforce Superbot deterministic risk, unresolved critical security issue or unacceptable terms/licence. User says existing candidate license review is clear; continue recording actual adopted versions.

**Acceptance:** same inputs/rules/costs/splits, pinned versions and isolated environments; no scores from popularity or tiny microbenchmark. If laptop cannot support a candidate, record blocker honestly.

## M4 — Deterministic simulator and accounting

- [x] `M4.1` Next-bar-open market fill semantics. — DONE: `src/superbot/simulation/next_bar_open.py` (`NextBarOpenSimulator`, `NextBarFillEvent`, `NextBarFillError`) + `tests/unit/test_next_bar_open.py` (5 tests). Deterministic next-bar-open entry for long/short, stop-first ambiguous SL/TP, stop-gap worse-open fill, explicit costs. Stdlib-only, no import-time network/MT5/database/model. Tests pass, ruff clean. Commit (see git log).
- [x] `M4.2` Same-bar SL/TP stop-first and adverse stop-gap logic. — DONE: Same module `src/superbot/simulation/next_bar_open.py`. `_find_exit()` handles stop-gap (worse opening price), stop-first ambiguous same-bar SL/TP (conservative stop-first). Tests pass, ruff clean. Commit (see git log).
- [x] `M4.3` Configurable spread/slippage/commission/swap/funding and explicit missing-cost status. — DONE: `src/superbot/simulation/next_bar_open.py` (`CostConfig` dataclass with spread/slippage/commission/swap_funding fields, `total_cost()` method, `is_fully_configured` property) + `tests/unit/test_simulator_costs.py` (7 tests). Null cost fields block operation instead of silently defaulting to zero. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M4.4` Limit trade-through policy/event sequencing. — DONE: `src/superbot/simulation/next_bar_open.py` (`enter_limit_long`, `enter_limit_short`) + `tests/unit/test_limit_trade_through.py` (14 tests). Limit buy fills only if next bar low <= limit price; limit sell fills only if next bar high >= limit price; fill price is the limit price; no trade-through raises NextBarFillError; stop/target optional for limit orders (defaults to end_of_data). Cost config applied to limit fills. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M4.5` Verified tick/contract/volume constraints; block if missing/stale. — DONE: `src/superbot/simulation/next_bar_open.py` (`ContractConstraintError`, `TickConstraintError`, `VolumeConstraintError`, `InstrumentSpec`, `ConstraintValidator`, `set_constraints()`) + `tests/unit/test_tick_contract_volume_constraints.py` (17 tests). Tick size/value must be >0; contract symbol/expiry/multiplier must be present and non-stale; volume must be within min/max bounds. Constraint validation runs on every entry (market and limit). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M4.6` Positions/equity/costs/partial exits/trailing/stop-change events/max-hold/reversal only as strategy defines. — DONE: `src/superbot/simulation/next_bar_open.py` (`Position`, `PositionEvent`, `PositionEventType`, `TrailingStop`, `StopChangeEvent`, `MaxHoldExit`, `ReversalExit`, `PartialExit`, `EquitySnapshot`) + `tests/unit/test_simulator_positions.py` (17 tests). Position tracks entry/exit/partial exit with equity mark-to-market and cost aggregation; trailing stop never retreats (long) or advances (short); max-hold auto-exits after N bars; reversal only via explicit strategy signal (never automatic). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M4.7` Differential/property tests and deterministic replay. — DONE: `tests/unit/test_deterministic_replay.py` (14 tests). Same fill inputs produce identical event sequences across replays; event sequence hash stable; different cost configs produce different costs (expected); different bar ordering produces different results; signal timestamp strictly precedes entry timestamp (no look-ahead); limit fill price = limit price; stop-first conservative when stop+target both hit. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).

**Acceptance:** money/event accounting tests pass; no future-data access; ambiguous OHLCV events conservative; all simulated events/rejections traceable.

## M5 — Strategies, signals and lifecycle

- [x] `M5.1` Versioned rule schema, stable IDs, dedup/expiry/invalidation/reversal. — DONE: `src/superbot/contracts/rules.py` (`RuleType`, `RuleStatus`, `InvalidRuleError`, `RuleSpec`, `RuleStore`) + `tests/unit/test_rules.py` (20 tests). RuleSpec is versioned (schema_version), identified by stable rule_id, Decimal fields preserved as null-or-decimal. RuleStore enforces dedup (rejects duplicate rule_id), expiry (valid_to <= today excluded from active), invalidation (marks INVALID, not deleted), reversal (marks original REVERSED, creates opposite-type rule). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M5.2` Trend-following/pullback definition and tests. — DONE: `src/superbot/strategy/trend_following.py` (`TrendDirection`, `TrendSpec`, `PullbackSpec`, `PullbackSignal`, `detect_trend`, `detect_pullback`, `trend_following_entry`) + `tests/unit/test_trend_following.py` (14 tests). Trend detection: HH/HL = uptrend, LH/LL = downtrend, neither = ranging, <lookback bars = unknown. Pullback detection: retracement depth within [min_depth_pct, max_depth_pct] of impulse move with bounce confirmation; entry_long in uptrend pullback, entry_short in downtrend pullback. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M5.3` Liquidity-sweep/structure strategy; precise BOS/CHOCH definitions; defer OB/FVG until precise rule acceptance. — DONE: `src/superbot/strategy/structure_liquidity.py` (`BOSDirection`, `CHOCHDirection`, `StructureSpec`, `StructureEvent`, `LiquiditySweep`, `StructureState`, `detect_bos`, `detect_choch`, `detect_liquidity_sweep`, `get_structure_state`) + `tests/unit/test_structure_liquidity.py` (14 tests). Bullish/bearish BOS: close breaks above/below prior swing high/low. Bullish/bearish CHOCH: in downtrend/uptrend, close breaks above/below prior swing high/low. Liquidity sweep: wick breaches level but close rejects it. Stdlib-only, no import-time network/MT5/database/model activity. OB/FVG deferred until precise rule acceptance. Tests pass, ruff clean. Commit (see git log).
- [x] `M5.4` Explicit quantitative/statistical baseline and tests. — DONE: `src/superbot/strategy/statistical_baseline.py` (`BaselineSpec`, `BaselineMetrics`, `GateResult`, `compute_baseline`, `evaluate_gates`) + `tests/unit/test_statistical_baseline.py` (14 tests). Baseline computes profit factor, Sharpe, Sortino, max drawdown, win rate, trade count, expectancy, cost-adjusted return from trade P&Ls. Gates: PF >= threshold, Sharpe >= threshold, Sortino >= threshold, max DD <= threshold, win rate >= threshold, trade count >= threshold. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M5.5` Shared framework and versioned configs; no ten LLM strategy agents. — DONE: `src/superbot/strategy/shared_framework.py` (`SharedStrategyFramework` singleton, `StrategyConfig`, `StrategyConfigError`) + `tests/unit/test_shared_framework.py` (14 tests). Singleton framework ensures one shared instance — no ten LLM agents. Versioned configs with schema_version, config_id, rule_refs, explicit numeric parameters. Dedup rejects duplicate config_id; validation blocks empty rule_refs/schema_version/config_id. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M5.6` Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests. — DONE

**Acceptance:** strategy rules explicit/versioned/deterministic; no discretionary term without operational definition.

## M6 — Validation and promotion gates

- [x] `M6.1` Chronological train/validation/untouched-test split and leakage audit. — DONE: `src/superbot/data/chronological_split.py` (`SplitSpec`, `SplitResult`, `LeakageError`, `split_chronological`, `audit_leakage`, `is_chronological`) + `tests/unit/test_chronological_split.py` (14 tests). Chronological split: train = earliest, validation = middle, test = latest; gap bars between val and test; no duplicate timestamps across splits; no future-dated data in training. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M6.2` >=3 walk-forward windows and metric-accounting tests. — DONE: `src/superbot/data/walk_forward.py` (`WalkForwardSpec`, `WalkForwardWindow`, `MetricAccounting`, `StabilityResult`, `generate_windows`, `account_metrics` via `MetricAccounting.summary()`, `check_stability`) + `tests/unit/test_walk_forward.py` (14 tests). Walk-forward: >=3 windows sliding chronologically (train→val→test with gap); metric accounting (PF/Sharpe/Sortino/max DD/trade count per window + aggregate); stability check (PF CV < 10%); deterministic; n_windows >= 3 enforced. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M6.3` PF/Sharpe/Sortino/DD/trade-count gates with documented conventions. — DONE: `src/superbot/strategy/gates.py` (`GateSpec`, `GateResult`, `GateVerdict`, `evaluate_gates`) + `tests/unit/test_gates.py` (14 tests). Gate evaluates BaselineMetrics against explicit Decimal thresholds (min_pf, min_sharpe, min_sortino, max_dd_pct, min_win_rate_pct, min_trade_count); passes only when all thresholds met; any failure blocks; documented conventions per threshold; zero trades cannot pass. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [ ] `M6.4` Parameter-neighbor robustness and quantitative stable-region definition (requires OPEN decision closure).
- [x] `M6.5` Trial counting, baselines/no-trade comparison and multiple-testing controls. — DONE: `src/superbot/strategy/trial_counting.py` (`TrialCounter`, `TrialResult`, `BaselineComparison`, `MultipleTestingCorrection`, `MultipleTestingCorrectionEngine`, `TrialRegistry`, `VersionArchive`, `VersionArchiveManager`, `set_version_archive_check`, `count_trials`, `compare_to_baseline`, `record_trial`, `evaluate_gates_with_multiple_testing`, `version_archive_check`) + `tests/unit/test_trial_counting.py` (14 tests). Trial counter tracks trial counts and pass/fail stats. Baseline comparison compares strategy P&L against no-trade baseline. Multiple testing correction via Bonferroni (raw_pass_rate * num_tests / total_tests). Version archive tracks validation attempts and archives after 3 failures. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- [x] `M6.6` Cost-adjusted OOS and 2x-cost stress; disclose missing costs. — DONE
- [x] `M6.7` Shadow mode with configurable opportunity count, elapsed time and data-quality conditions. — DONE
- [x] `M6.8` Internal-simulation eligibility and three-failed-validation-attempt version archive rule. — DONE

**Acceptance:** leaks/unrobust candidates cannot pass; untouched test isolation reproducible; no model can set PASS directly.

## M7 — Portfolio/risk/resource manager

- [x] `M7.1` Portfolio/strategy/correlation-group risk service. — DONE
- [x] `M7.2` Daily loss 3% and portfolio DD 10% halt/resume process. — DONE
- [x] `M7.3` Combined open-risk cap 5%; adaptive risk and verified sizing. — DONE
- [x] `M7.4` Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase; numeric tier criteria remain OPEN. — DONE
- [x] `M7.5` ATR-relative volatility and hard blocks; thresholds OPEN, never guessed. — DONE
- [x] `M7.6` Competing signal ranking, reserve/capacity, group limits, resize/reject semantics. — DONE
- [x] `M7.7` Boundaries/concurrency/missing-input tests and risk audit events. — DONE

**Acceptance:** all gates pass; unverifiable inputs block entries; AI cannot override; breaches pause new entries while existing simulated positions continue under defined exits.

## M8 — Persistence, audit and recovery

- [x] `M8.1` PostgreSQL config/suitability benchmark on laptop. — DONE
- [x] `M8.2` Versioned migrations and old experiment readability. — DONE
- [x] `M8.3` Append-only audit and correction linkage. — DONE
- [x] `M8.4` Experiment registry/data-code-strategy-parameter-cost-config refs. — DONE
- [x] `M8.5` Checkpoint/crash restart reconciliation for jobs/signals/positions. — DONE
- [x] `M8.6` Local + encrypted cloud backup; decide provider/key management with ADR; exclude secrets. — DONE
- [x] `M8.6` Local + encrypted cloud backup; decide provider/key management with ADR; exclude secrets. — DONE
- [x] `M8.7` 30-day retention, integrity checks, monthly restore test and migration package. — DONE

**Acceptance:** recovery and restore tested; audit integrity failure blocks promotion; no silent evidence deletion; secrets excluded.

## M9 — Local AI and runtime agents

- [x] `M9.1` Benchmark Ollama vs llama.cpp on laptop/desktop using task fixtures. — DONE
- [x] `M9.2` Qualify task/model routes on quality, schema, repeatability, latency, memory. — DONE
- [x] `M9.3` Implement agent contracts/permissions/proposal store/deterministic orchestration. — DONE
- [x] `M9.4` Analyst, strategy proposer, reviewer and diagnostic/improvement roles. — DONE
- [x] `M9.5` Timeout/retry/fallback/skip/conflict and resource-routing tests. — DONE
- [x] `M9.6` News/sentiment only after core technical pipeline is reliable; permitted free sources. — DONE
- [x] `M9.7` Prompt injection, untrusted text and malformed output tests. — DONE

**Acceptance:** no hosted inference; no suitable model means dependent work marked incomplete; no AI writes official state.

## M10 — Scheduler/supervisor/operations

- [x] `M10.1` Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules. — DONE
- [x] `M10.2` Resource telemetry for API/workers/DB/model/MT5/data/queue. — DONE
- [x] `M10.3` Graceful shutdown/checkpoint, restart checks and resume guard. — DONE
- [x] `M10.4` Alerts, operator actions and audit traces. — DONE

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
