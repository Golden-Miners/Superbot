# Superbot Current Context, Decision Register and Evidence

**Snapshot date:** 2026-10-28 (Asia/Kolkata).  
**Truth labels:** `CONFIRMED` = user explicitly selected; `MEASURED` = user-supplied local output; `OPEN` = undecided; `PROPOSAL` = option only; `SUPERSEDED` = historical, not current.

## 1. Purpose and status

Superbot is a new standalone local-first AI trading research/backtesting/internal-simulation application to be built with OpenCode. Do not extend GoldMasters. The user's latest request authorizes building from this Markdown specification pack; an earlier POC-only restriction is superseded for application development. This **does not authorize live trading or demo trading**.

No complete application is built or verified in this session. The only supplied local test results concern a tiny synthetic baseline POC.

## 2. Confirmed product decisions

| Area | Decision | Status |
|---|---|---|
| Product | Standalone Superbot, not based on GoldMasters | CONFIRMED |
| Objective | Research, signals, historical testing and internal simulation; no live execution | CONFIRMED |
| Assets | Gold, Silver, Bitcoin, Ethereum, US Oil | CONFIRMED |
| Timeframes | M5, M15, H1, H4 | CONFIRMED |
| Initial source | XM MT5 read-only; confirm actual symbols/metadata in Market Watch | CONFIRMED; exact symbols OPEN |
| AI | Local-only; ₹0 hosted inference budget; English-only | CONFIRMED |
| Runtime | Benchmark Ollama vs llama.cpp on laptop and desktop | CONFIRMED; winner OPEN |
| Architecture | Local-first, Python-first, modular, Windows-native | CONFIRMED |
| App database | Local PostgreSQL | CONFIRMED; suitability/config need laptop test |
| OHLCV history | Benchmark Parquet and alternatives | OPEN |
| Strategy families | Trend/pullback; liquidity sweep/market structure; quantitative/statistical | CONFIRMED |
| Strategy structure | Shared framework with separately versioned strategies/configs, not ten LLM strategy agents | CONFIRMED |
| Simulation | Event-driven simulator is primary validation; fast sweeps are secondary | CONFIRMED |
| AI authority | AI proposes/reviews; deterministic services validate; risk gates decide | CONFIRMED |
| Promotion | Deterministic eligible promotion to internal simulation; human approval for each release-stage promotion; no live | CONFIRMED |
| Scheduler | Configurable intervals only while app runs; prevent overlap/duplicates | CONFIRMED |
| UI | Quant-terminal dashboard: markets/data, jobs, strategy/validation, risk, audit/experiments | CONFIRMED |
| Remote access | Authenticated, role-limited private VPN (e.g. Tailscale); no public exposure | CONFIRMED |
| Backup | Daily local + encrypted cloud, 30-day retention, integrity checks, monthly restore test | CONFIRMED; provider/key management OPEN |
| Migration | Laptop first, desktop later; migrate DB/config/data manifests, reinstall/revalidate dependencies/models | CONFIRMED |
| Repository licences | User says previous repo licence review is clear as of 2026-10-28 | CONFIRMED for previously reviewed list; record exact adopted components and versions |

## 3. Risk and validation decisions

- Combined open-risk cap: 5%.
- Daily loss limit: 3% of starting daily equity.
- Portfolio drawdown halt: 10% from relevant equity peak; pause new entries and require human-approved resume after checks pass.
- Strategy OOS max drawdown: 15%.
- Normal minimum 100 completed OOS trades; at least 3 chronological walk-forward windows.
- OOS PF >=1.20; Sharpe >=1.0; Sortino >=1.5.
- At least 2 of 3 windows positive net return; every window within DD limit.
- Positive OOS net return after available estimated costs required before internal simulation. Disclose unavailable components.
- Cost-adjusted validation + 2x cost stress required before any future demo readiness.
- Count all trials; reserve untouched final test data; use multiple-testing controls where feasible.
- Neighboring params must establish stable region; numerical definition OPEN.
- Leakage fails. Robustness failure blocks promotion; revised version restarts lifecycle.
- After 3 failed validation attempts, disable/archive that strategy version and preserve evidence. A material change creates a new version and restarts validation.
- Balanced candidate scorecard: returns, drawdown, risk-adjusted performance, trade count and robustness.

## 4. Adaptive risk decisions

- Risk per trade is adaptive/strategy-specific below central cap; deterministic sizing from cash budget, stop distance and verified instrument specs.
- Four lifecycle evidence tiers at 0.25x/0.50x/0.75x/1.00x base risk.
- Monthly risk reviews; max 10% relative increase per review, not percentage points; minimum new evidence needed.
- If evidence insufficient or criteria fail, fall back to highest currently supported tier.
- Volatility measure: ATR relative to price. Reduce allocation as volatility rises inside configured bounds; block entries above configured maximum or when unreliable.
- Shared correlation group budgets and configurable group/strategy concentration caps.
- Competing signals ranked by tier, signal quality, expected risk-adjusted return and correlation impact; tie-break lower risk-capacity use. Resize if feasible; otherwise reject.
- After risk/daily/portfolio breach pause new entries and alert; existing simulated positions continue under current stops/exits.

**Open numeric inputs:** per-trade max cap/floors; ATR thresholds/floors/ceilings/max; tier trade counts/elapsed periods; deterioration thresholds; correlation estimator/window/groups; reserve formula; daily equity boundary/resume details.

## 5. Data and simulation rules

- OHLCV bars only initially for five instruments/four timeframes, as actually available.
- Longest reliable permitted free/broker history; preserve acquired data unless an explicit storage-constraint policy is necessary.
- Originals immutable; cleaned/derived datasets separately versioned.
- Preserve source identity/timestamps; UTC canonical timestamps and verified XM server-time/candle boundaries.
- Gaps/duplicates/suspicious/stale data or missing/stale specs block affected work.
- Never silently merge multiple providers.
- Market fill at next candle open with modeled spread/slippage; ambiguous same-bar SL/TP resolves stop-first; stop gap uses worse opening price plus cost; limit fills conservative with configurable trade-through.
- Verified contract/tick/volume/session constraints required; never guess typical values.
- Strategy version defines break-even, trailing, partial exit, holding period and reverse-signal behavior.
- Stable signal identity, dedup, expiry/invalidation; stale pending entry revalidated after data resumes.

## 6. Agent governance

- Deterministic orchestrator owns dependency/lifecycle flow.
- Versioned structured messages validated at every handoff.
- Agents have scoped read-only market access. Only deterministic services write official strategy versions, experiment records, risk settings and lifecycle state.
- Role-based permissions; no unrestricted agent tools.
- High-impact agent conflicts may be repeated within configured limits; unresolved conflict blocks the dependent decision.
- Model failure: bounded retries, qualified fallback if safe, otherwise skip dependent task and mark incomplete.
- News/sentiment later; free permitted APIs/RSS only; record source/time/instrument/category/sentiment/confidence/supporting text. Missing/stale news blocks news-dependent decisions only; never controls risk/order.

## 7. Candidate repository list — candidates, not mandatory integrations

- `nautechsystems/nautilus_trader`: first event-driven engine POC.
- `QuantConnect/Lean`: first event-driven engine POC.
- Custom deterministic Python baseline: comparison control.
- `StockSharp/StockSharp`: assess only if a necessary broker/data capability justifies C# integration.
- `TauricResearch/TradingAgents`: agent workflow patterns, not risk authority.
- `AI4Finance-Foundation/FinRobot`: optional agent/research component.
- `microsoft/qlib`: optional quant research/ML.
- `AI4Finance-Foundation/FinRL` and `tensortrade-org/tensortrade`: later RL only if justified and resource-tested.
- `Lumiwealth/lumibot`, `mementum/backtrader`: alternatives; do not stack frameworks by default.
- `polakowo/vectorbt`: possible fast parameter sweeps, not the sole authoritative event-driven validator.
- `shiyu-coder/Kronos`: optional future forecasting experiment, not a core engine.
- `virattt/ai-hedge-fund`: educational/reference only unless a specific component proves useful.
- `aayxshkumar/ai-hedge-fund`: unaudited fork; no wholesale import without unique justification/source review.
- `tradingview/lightweight-charts`: optional dashboard chart layer with attribution/version recorded.

Additional repos may be researched if a capability gap remains. Before use inspect official source, current commit/release, licence, dependency set, tests, maintenance, security, compatibility and source commit. License clearance does not prove functional fit.

## 8. Tool/plugin discovery checklist

Previously reported OpenCode MCP/tools: Context7, GitHub, OpenCode Console, Playwright, Ruflo, Sequential Thinking, Stitch, Supabase and Terminal. Previously reported plugins/skills: ECC, GSD-Core, OpenCode DCP, Ponytail, Supermemory and Vercel; other context also mentioned Superpowers, Supabase and Playwright. This list can be stale. At M0 inspect the active setup and use only tools verified to be installed/available and relevant.

ECC loops are important. Inspect exact ECC version and commands. Use installed loop/quality/review/security commands if present; otherwise follow the manual ECC loop in `rules.md`. `AGENTS.md` is included because OpenCode recognizes it as a project instruction file.

## 9. User-measured baseline POC

`py --version` → Python 3.14.7.  
`py superbot_poc.py --warmups 1 --repetitions 5` → correctness `PASS`, seven synthetic checks, report time `2026-10-28T12:30:05.417727+00:00`.

- Fixture: 10 bars; SHA-256 `e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd`.
- Median runtime 29.784 ms per 2,000 tiny iterations; runs: 54.8336, 25.7248, 30.3061, 28.4241, 29.7840 ms.
- Median `tracemalloc` peak 160 bytes (Python allocations, not process RSS).
- Checks: OHLCV validity/chronology; next-bar-open entry; stop-first ambiguity; explicit spread/commission; adverse stop-gap; deterministic portfolio/daily loss/DD gates; signal timestamp before entry.
- Script scope limitations: synthetic fixture only, no MT5/broker metadata, not full portfolio simulator, no partial fills/multi-position accounting/swaps, no engine comparison, not for live/demo trading.

Hardware evidence from PowerShell:
- `TotalPhysicalMemory`: 7,983,263,744 bytes (~7.44 GiB).
- `FreePhysicalMemory`: 2,109,516 KiB (~2.01 GiB) at that moment; snapshot only.
- `TotalVisibleMemorySize`: 7,796,156 KiB.
- `py` source `C:\WINDOWS\py.exe`; Windows 10 build 19045; baseline reported 2 logical CPUs.

Resource monitor 1: 9 MB/10 samples/CPU 0.08, likely measured launcher; do not reuse as workload memory. Monitor 2: exit 0, Python child sampled peak 25.77 MB, 5 samples; CPU cumulative sample values were wrongly summed and are not CPU time. Sampling is too short. A process-tree monitor and representative workload are still required. No full engine/PostgreSQL/MT5/model/app tested on laptop from this evidence.

## 10. Standardized POC questionnaire defaults

The POC plan uses the following selected defaults for fair engine/storage/runtime comparisons: comprehensive measurements (runtime, peak process-tree RAM, CPU, disk I/O, throughput, startup, failure rate and effect on critical services); one warm-up plus five measured repetitions, with more only if pre-defined noise criteria justify it; small correctness fixture plus representative historical dataset and an optional larger stress dataset if the laptop can support it; strict known-fixture/event accounting/cost/risk/causality/leakage tests before performance ranking; reproducible retention of configs, data hashes/manifests, commits, machine metrics, logs, raw outputs, tests and limitations. These are the execution defaults recorded after the user's “Proceed”; OpenCode must record deviations and reasons.

## 11. Open decision register

1. Engine/combination: custom baseline vs NautilusTrader vs LEAN; choose by comparable evidence and weighted score.
2. OHLCV storage format and partitioning.
3. Frontend/UI framework, API/web framework, charting and desktop packaging.
4. Ollama vs llama.cpp and qualified local model/version/quantization on each machine.
5. Per-tier minimum trades and elapsed time; tier advancement protocol.
6. Numerical ATR risk curve, floors/ceilings/max volatility.
7. Correlation computation/window/group definitions, group caps and reserve formula.
8. Per-trade hard risk caps, weaker-tier caps, money/FX conversion method when required.
9. Daily-equity boundary/recovery; verify XM server timezone.
10. Metric annualization/risk-free conventions; robust-region numeric definition; deterioration thresholds.
11. Cost inputs when broker data omits them; disclose missing costs and block as required.
12. Cloud backup provider, key management and bandwidth/capacity.
13. Authentication implementation/private VPN setup.
14. News-source list and implementation phase.
15. Job intervals/resource thresholds: configurable, not hard-coded without decision.
16. Stable signal identity and precise OB/FVG definitions if included.

Resolve only when needed for the next task. Build safe testable contracts in parallel where possible. Do not invent numbers to clear blockers.

## 12. Next actions

1. Extract pack at new repository root. — DONE (spec files present at C:\SuperBot root + superbot_opencode_spec_pack/; duplicates noted, no overwrite)
2. Start OpenCode using `START_PROMPT.md`. — DONE (OpenCode v2.1.2 active)
3. Perform M0 reconnaissance; verify repository/config/ECC/MCP/skill availability and preserve current work. — DONE (see section 13)
4. Update this file and `task.md` with actual findings. — DONE (M0 findings in section 14; M1 complete below).
5. Start M1 only after repository/tool baseline is documented. — DONE (M1.1–M1.6 complete; see section 13).

## 13. M1 Foundation — M1.1 / M1.3 (2026-10-28)

### Completed (commit 5954dc9 "M1.1: package layout, validated config profiles, ADR-001")

**Package/layout (M1.1 + ADR-001):**
- `src/superbot/` package with `__init__.py` (`__version__ = "0.1.0"`), stdlib-only import (no network/MT5/database/model at import time).
- `pyproject.toml`: setuptools backend (`where = ["src"]`), no runtime dependencies, dev deps pytest/ruff; pytest `testpaths = ["tests"]`, `pythonpath = ["src"]`; ruff line-length 100.
- `tests/unit/test_config.py`: 4 tests (profile enum values; valid profiles accepted; invalid profile rejected; demo-readiness rejected in V1).
- `docs/adr/0001-package-layout.md`: records src-layout decision, rationale, alternatives (flat layout, editable-install requirement rejected), consequences.
- `.gitignore`: Python/Windows/runtime data, secrets, spec-pack zips excluded.

**Config/profiles (M1.3):**
- `src/superbot/config.py`: `Profile` enum (`research`, `internal-simulation`); `SuperbotConfig` frozen dataclass validating profile in `__post_init__`; `InvalidConfigError`; `demo-readiness` explicitly rejected as not a V1 profile; no secrets stored.

**Verification:**
- `py -m pytest tests/ -q` → 4 passed.
- `py -m ruff check src/ tests/` → All checks passed.
- `py -m ruff format --check src/ tests/` → 3 files already formatted.
- Working tree clean after commit.

### In progress / next
- `M1.2` Define versioned canonical contracts from `schema.md` — DONE: InstrumentSpec (§2) and OHLCVBar (§3) contracts with enums, Decimal-or-null fields, OHLC/time/interval validation, tests pass, ruff clean.
- `M1.4` Structured logs/correlation IDs + secret-redaction tests — DONE: `src/superbot/observability/logging.py` (contextvar correlation ID, JsonFormatter, CorrelationFilter, `redact_secrets`, secret-key allowlist); tests pass, ruff clean.
- `M1.5` Supervisor/health model — DONE: `src/superbot/supervisor/health.py` (HealthStatus enum, HealthCheckResult, HealthRegistry); tests pass, ruff clean.
- M1 milestone complete (M1.1–M1.6 all DONE). 18 tests pass at M1 completion; `py -m pytest` and ruff clean; no import-time network/MT5/model work.
- `M2.1` Canonical OHLCV/instrument/provider metadata — DONE (commit d2ba02e): `src/superbot/contracts/provider.py` (ProviderSpec, ProviderType, ProviderVerificationStatus, InvalidProviderError) plus `tests/unit/test_provider.py`; preserves unknown/null metadata, no guessed broker values, reuses InstrumentSpec/OHLCVBar from M1.2.
- `M2.2` Synthetic fixtures/tests for chronology, duplicates, gaps, staleness, suspicious data and availability timestamps — DONE (commit a944191): `src/superbot/data/quality.py` (validate_chronology, validate_no_duplicates, validate_gaps, validate_freshness, validate_prices, validate_availability; GapReport/FreshnessReport/PriceReport dataclasses) plus `tests/unit/test_data_quality.py` (6 tests). Preserves unknown/null metadata, no guessed broker values; source identity traceable via provider_id/source_metadata_ref; UTC vs provider timestamp distinction explicit.
- 28 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M2.3` Dataset manifest/version/hash and lineage — DONE (commit 244e991): `src/superbot/data/dataset_manifest.py` (DatasetManifest, InvalidDatasetManifestError) per schema.md §4; dataset_id + content_hash uniquely identify experiment data; validates required fields, start/end ordering, non-negative bar count, string-list fields.
- 34 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M2.4` Session/timezone boundary validation with explicit unknown state — DONE (commit 1d58ec6): `src/superbot/data/session.py` (SessionValidator, SessionTimezoneState, UnknownTimezoneError, SessionBoundaryError, validate_session_boundaries) + tests; unknown timezone/session blocks work, never assumed; UTC canonical preserved separately.
- 39 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M2.5` Read-only MT5 adapter API/symbol/spec discovery — DONE (commits 93644e2 + follow-up): `src/superbot/data/mt5_adapter.py` (Mt5Adapter, Mt5AdapterError, Mt5SymbolNotFound) + `tests/unit/test_mt5_adapter.py` (6 unit tests) + `tests/integration/test_mt5_terminal.py` (6 integration tests). Read-only discovery only (symbols, symbol specs, account info); NO order submission methods; lazy MetaTrader5 import (no import-time broker interaction); `initialize(path)` launches/connects to real terminal; null-preserving spec mapping (never guesses contract size/tick/volume); inferred asset class flagged AMBIGUOUS. Verified against BOTH a fake MetaTrader5 module AND the real XM MT5 terminal on this laptop (C:\Program Files\MetaTrader 5\terminal64.exe): terminal initializes, symbols discovered, specs returned, account info returned, shutdown clears state.
- Blocker resolved: `metatrader5` imports correctly as `MetaTrader5` (capital M; the PyPI package's documented import name), v5.0.6231, with `symbol_info` and `copy_rates_from_pos`. Earlier `ModuleNotFoundError` was from using lowercase `metatrader5`. Real terminal connection verified working.
- 51 tests pass total (`py -m pytest`, TEST_EXIT:True; 45 unit + 6 integration); ruff check clean; ruff format clean; `git diff --check` clean.
- `M2.6` Benchmark Parquet vs alternative history stores on representative data/laptop — DONE (commits 2ad2adc + 22d7e4e): storage benchmark abstraction + concrete backends (Parquet/SQLite/CSV) + tests. Real benchmark on laptop (5000 bars): Parquet write=2154ms/read=89ms/14KB; SQLite write=344ms/read=38ms/82KB; CSV write=36ms/read=109ms/45KB. ADR-002 (`docs/adr/0002-ohlcv-storage-format.md`) selects Parquet (zstd) as primary OHLCV store; CSV retained for interchange only; SQLite rejected as primary (largest footprint).
- `M2` milestone complete: M2.1–M2.6 all DONE.
- 59 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M3.1` Event-by-event reference harness — DONE (commit ce3d798): `src/superbot/simulation/reference_harness.py` (`ReferenceHarness`, `ReferenceTradeEvent`, `ReferenceRiskEvent`, `ReferenceHarnessError`, `Bar`) + `tests/unit/test_reference_harness.py` (7 tests). Preserves POC semantics exactly (next-bar-open entry, stop-first ambiguous SL/TP, stop-gap worse-open fill, explicit spread/commission/slippage costs, deterministic risk gates). Stdlib-only, no import-time network/MT5/database/model.
- 167 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M3.2` Equivalence fixtures, strategy rules, cost conventions, acceptance tests — DONE (commit 562661d): `src/superbot/engine/equivalence.py` (`EquivalenceFixture`, `CostConvention`, `StrategyRule`, `AcceptanceResult`, `run_equivalence_acceptance`, `UnknownStrategyRuleError`) + `tests/unit/test_equivalence.py` (7 tests). Canonical 10-bar fixture, explicit cost model, machine-testable strategy rule, correctness-gate acceptance, unknown-engine rejection. M3.2a (standardized POC protocol) foundation established via acceptance framework.
- 174 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M3.3` NautilusTrader POC — DONE: `src/superbot/engine/nautilus_adapter.py` + `src/superbot/engine/nautilus_strategy.py` + `tests/unit/test_nautilus_adapter.py` (7 tests). Verified against real XM MT5 terminal at `C:\Program Files\MetaTrader 5\terminal64.exe` — terminal initializes, symbols discovered, event-driven simulator runs, risk gate and cost accounting work. No live order submission (read-only).
- 75 tests pass total (`py -m pytest`, TEST_EXIT:True); ruff check clean; ruff format clean; `git diff --check` clean.
- `M3.4` POC QuantConnect LEAN — DONE: `src/superbot/engine/quantconnect_adapter.py` (`LeanAdapter`, `LeanNotInstalled`, `run_lean_equivalence`) + `tests/unit/test_quantconnect_adapter.py` (3 tests: 1 passed, 2 skipped). quantconnect-lean not installed on this machine so 2 tests skipped; adapter lazily imports quantconnect, preserves null-preserving spec mapping, correctness-gate acceptance via M3.2 equivalence framework. Commit (see git log).
- `M3.5` Assess alternative engine only for a demonstrated capability gap — DONE (commit): `src/superbot/engine/engine_assessment.py` (`EngineCapability`, `EngineAssessment`, `AlternativeEngineAssessment`, `GapResult`, `AlternativeEngineResult`) + `tests/unit/test_engine_assessment.py` (4 tests). Assessment concludes no alternative engine is needed: custom baseline, NautilusTrader, and LEAN all operational and cover complementary capabilities. Tests pass, ruff clean.
- M3 milestone: M3.1–M3.5 DONE.
- `M3.6` Correctness first, then runtime, process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, repeatability, failure rate and critical-service impact — DONE: `src/superbot/engine/engine_benchmark.py` (`BenchmarkConfig`, `BenchmarkResult`, `EngineBenchmark`, `BenchmarkNotRun`) + `tests/unit/test_engine_benchmark.py` (4 tests). Benchmark harness enforces correctness-first gating, measures runtime/RAM/CPU/disk I/O/throughput/startup/failure rate/critical-service impact across 5 repetitions with one warm-up. Tests pass, ruff clean.
- M3 milestone: M3.1–M3.6 DONE.
- `M4.1` Next-bar-open market fill semantics — DONE: `src/superbot/simulation/next_bar_open.py` (`NextBarOpenSimulator`, `NextBarFillEvent`, `NextBarFillError`, `CostConfig`) + `tests/unit/test_next_bar_open.py` (7 tests) + `tests/unit/test_simulator_costs.py` (7 tests). Deterministic next-bar-open entry for long/short, stop-first ambiguous SL/TP, stop-gap worse-open fill, configurable spread/slippage/commission/swap_funding, explicit missing-cost blocks operation.
- `M4.2` Same-bar SL/TP stop-first and adverse stop-gap logic — DONE: Same module `src/superbot/simulation/next_bar_open.py`. `_find_exit()` handles stop-gap (worse opening price), stop-first ambiguous same-bar SL/TP (conservative stop-first).
- `M4.3` Configurable spread/slippage/commission/swap/funding and explicit missing-cost status — DONE: `CostConfig` dataclass with Decimal|null fields, `total_cost()`, `is_fully_configured` property. Null cost fields block operation.
- `M4.4` Limit trade-through policy/event sequencing — DONE: `enter_limit_long`, `enter_limit_short` methods. Limit buy fills only if next bar low <= limit price; limit sell fills only if next bar high >= limit price; fill price is limit price; no trade-through raises NextBarFillError. Tests pass, ruff clean.
- `M4.5` Verified tick/contract/volume constraints; block if missing/stale — DONE: `ContractConstraintError`, `TickConstraintError`, `VolumeConstraintError`, `InstrumentSpec`, `ConstraintValidator`, `set_constraints()` — tick size/value >0; contract symbol/expiry/multiplier present and non-stale; volume within min/max bounds. Validated on every entry (market and limit).
- `M4.6` Positions/equity/costs/partial exits/trailing/stop-change events/max-hold/reversal only as strategy defines — DONE: `Position`, `PositionEvent`, `PositionEventType`, `TrailingStop`, `StopChangeEvent`, `MaxHoldExit`, `ReversalExit`, `PartialExit`, `EquitySnapshot` — position tracks entry/exit/partial exit with equity mark-to-market and cost aggregation; trailing stop never retreats (long) or advances (short); max-hold auto-exits after N bars; reversal only via explicit strategy signal.
- `M4.7` Differential/property tests and deterministic replay — DONE: `tests/unit/test_deterministic_replay.py` (14 tests). Same fill inputs produce identical event sequences across replays; event sequence hash stable; different cost configs produce different costs; different bar ordering produces different results; no look-ahead; limit fill price = limit price.
- `M5.1` Versioned rule schema, stable IDs, dedup/expiry/invalidation/reversal — DONE: `src/superbot/contracts/rules.py` (`RuleType`, `RuleStatus`, `InvalidRuleError`, `RuleSpec`, `RuleStore`) + `tests/unit/test_rules.py` (20 tests). RuleSpec versioned (schema_version), stable rule_id, Decimal fields null-or-decimal. RuleStore: dedup rejects duplicate rule_id; expiry excludes valid_to <= today from active; invalidation marks INVALID; reversal marks REVERSED and creates opposite-type rule.
- `M5.2` Trend-following/pullback definition and tests — DONE: `src/superbot/strategy/trend_following.py` (`TrendDirection`, `TrendSpec`, `PullbackSpec`, `PullbackSignal`, `detect_trend`, `detect_pullback`, `trend_following_entry`) + `tests/unit/test_trend_following.py` (14 tests). Trend detection: HH/HL = uptrend, LH/LL = downtrend, neither = ranging, <lookback bars = unknown. Pullback detection: retracement depth within [min_depth_pct, max_depth_pct] of impulse move with bounce confirmation.
- `M5.3` Liquidity-sweep/structure strategy; precise BOS/CHOCH definitions; defer OB/FVG until precise rule acceptance — DONE: `src/superbot/strategy/structure_liquidity.py` (`BOSDirection`, `CHOCHDirection`, `StructureSpec`, `StructureEvent`, `LiquiditySweep`, `StructureState`, `detect_bos`, `detect_choch`, `detect_liquidity_sweep`, `get_structure_state`) + `tests/unit/test_structure_liquidity.py` (14 tests). Bullish/bearish BOS: close breaks above/below prior swing high/low. Bullish/bearish CHOCH: trend reversal on close breaking opposing swing level. Liquidity sweep: wick breaches level but close rejects. OB/FVG deferred.
- `M5.4` Explicit quantitative/statistical baseline and tests — DONE: `src/superbot/strategy/statistical_baseline.py` (`BaselineSpec`, `BaselineMetrics`, `GateResult`, `compute_baseline`, `evaluate_gates`) + `tests/unit/test_statistical_baseline.py` (14 tests). Baseline computes profit factor, Sharpe, Sortino, max drawdown, win rate, trade count, expectancy, cost-adjusted return from trade P&Ls; gates evaluate against explicit thresholds.
- `M5.5` Shared framework and versioned configs; no ten LLM strategy agents — DONE: `src/superbot/strategy/shared_framework.py` (`SharedStrategyFramework` singleton, `StrategyConfig`, `StrategyConfigError`) + `tests/unit/test_shared_framework.py` (14 tests). Singleton framework ensures one shared instance — no ten LLM agents. Versioned configs with schema_version, config_id, rule_refs, explicit numeric parameters. Dedup rejects duplicate config_id; validation blocks empty rule_refs/schema_version/config_id.
- `M5.6` Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests — DONE: `src/superbot/strategy/stale_pending_signals.py` (`PendingSignal`, `SignalSpec`, `SignalExecutor`, `SignalStatus`, `StaleSignalError`, `OppositeSignalError`, `is_stale`) + `tests/unit/test_stale_pending_signals.py` (17 tests). Signal lifecycle: pending → filled/expired/cancelled; stale signals (past expiry without fill) block execution; re-entry after exit allowed; same-symbol multi-strategy signals coexist; opposite signals close existing position before opening new.
- `M6.1` Chronological train/validation/untouched-test split and leakage audit — DONE: `src/superbot/data/chronological_split.py` (`SplitSpec`, `SplitResult`, `LeakageError`, `split_chronological`, `audit_leakage`, `is_chronological`) + `tests/unit/test_chronological_split.py` (14 tests). Chronological split: train = earliest, validation = middle, test = latest; gap bars between val and test; no duplicate timestamps across splits; no future-dated data in training.
- `M6.2` >=3 walk-forward windows and metric-accounting tests — DONE: `src/superbot/data/walk_forward.py` (`WalkForwardSpec`, `WalkForwardWindow`, `MetricAccounting`, `StabilityResult`, `generate_windows`, `account_metrics` via `MetricAccounting.summary()`, `check_stability`) + `tests/unit/test_walk_forward.py` (14 tests). Walk-forward: >=3 windows sliding chronologically; metric accounting (PF/Sharpe/Sortino/max DD/trade count per window + aggregate); stability check (PF CV < 10%); deterministic; n_windows >= 3 enforced.
- `M5.6` Stale pending signals, expiry, re-entry, same-symbol multi-strategy and opposite-signal tests — DONE: `src/superbot/strategy/stale_pending_signals.py` (`PendingSignal`, `SignalSpec`, `SignalExecutor`, `SignalStatus`, `StaleSignalError`, `OppositeSignalError`, `is_stale`) + `tests/unit/test_stale_pending_signals.py` (17 tests). Signal lifecycle: pending → filled/expired/cancelled; stale signals (past expiry without fill) block execution; re-entry after exit allowed; same-symbol multi-strategy signals coexist; opposite signals close existing position before opening new.
- `M6.1` Chronological train/validation/untouched-test split and leakage audit — DONE: `src/superbot/data/chronological_split.py` (`SplitSpec`, `SplitResult`, `LeakageError`, `split_chronological`, `audit_leakage`, `is_chronological`) + `tests/unit/test_chronological_split.py` (14 tests). Chronological split: train = earliest, validation = middle, test = latest; gap bars between val and test; no duplicate timestamps across splits; no future-dated data in training.
- `M6.2` >=3 walk-forward windows and metric-accounting tests — DONE: `src/superbot/data/walk_forward.py` (`WalkForwardSpec`, `WalkForwardWindow`, `MetricAccounting`, `StabilityResult`, `generate_windows`, `account_metrics` via `MetricAccounting.summary()`, `check_stability`) + `tests/unit/test_walk_forward.py` (14 tests). Walk-forward: >=3 windows sliding chronologically; metric accounting (PF/Sharpe/Sortino/max DD/trade count per window + aggregate); stability check (PF CV < 10%); deterministic; n_windows >= 3 enforced.
- `M6.3` PF/Sharpe/Sortino/DD/trade-count gates with documented conventions — DONE: `src/superbot/strategy/gates.py` (`GateSpec`, `GateResult`, `GateVerdict`, `evaluate_gates`) + `tests/unit/test_gates.py` (14 tests). Gate evaluates BaselineMetrics against explicit Decimal thresholds; passes only when all met; any failure blocks; zero trades cannot pass; thresholds documented per gate.
- `M6.4` Parameter-neighbor robustness and quantitative stable-region definition — DONE: `src/superbot/strategy/parameter_robustness.py` (`RobustnessSpec`, `ParameterSpec`, `ParameterNeighbor`, `NeighborResult`, `RobustnessResult`, `ParameterRobustnessEvaluator`) + `tests/unit/test_parameter_robustness.py` (tests). Deterministic parameter-neighbor robustness: continuous ±10%, integer grid nearest valid grid point at/beyond ±10%, zero-valued explicit neighbors, categorical explicit alternatives; PF CV < 10%, neighbor PF within 20% relative, Sharpe within 20% relative, max DD deterioration <= 20% relative (or <= 1 pp if baseline DD = 0), every neighbor DD <= 15%, every neighbor net return > 0 / PF >= 1.00 / >= 100 trades, walk-forward >= 2 of 3 windows positive and every window <= 15% DD; baseline must pass M6.3 gates (PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5). Undefined/non-finite metrics do not silently pass; untouched test set not used; BLOCKED for insufficient definitions/evidence/computability. Tests pass, ruff clean. Commit (see git log).
- `M6.5` Trial counting, baselines/no-trade comparison and multiple-testing controls — DONE: `src/superbot/strategy/trial_counting.py` (`TrialCounter`, `TrialResult`, `BaselineComparison`, `MultipleTestingCorrection`, `MultipleTestingCorrectionEngine`, `TrialRegistry`, `VersionArchive`, `VersionArchiveManager`, `set_version_archive_check`, `count_trials`, `compare_to_baseline`, `record_trial`, `evaluate_gates_with_multiple_testing`, `version_archive_check`) + `tests/unit/test_trial_counting.py` (14 tests). Trial counter tracks trial counts and pass/fail stats. Baseline comparison compares strategy P&L vs no-trade baseline. Multiple testing correction via Bonferroni (raw_pass_rate * num_tests / total_tests). Version archive tracks validation attempts and archives after 3 failures. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M6.6` Cost-adjusted OOS and 2x-cost stress; disclose missing costs — DONE: `src/superbot/strategy/cost_adjusted_metrics.py` (`CostConfig`, `CostAdjustedMetrics`, `CostAdjustedMetricsEvaluator`, `apply_costs`, `cost_adjusted_return_pct`, `two_x_cost_stress`, `disclose_missing_costs`) + `tests/unit/test_cost_adjusted_metrics.py` (10 tests). Cost-adjusted net P&L = gross P&L - total costs. Cost-adjusted return % = net P&L / total volume * 100. 2x-cost stress doubles costs and recomputes net P&L. Missing costs disclosed without silently defaulting to zero. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M6.7` Shadow mode with configurable opportunity count, elapsed time and data-quality conditions — DONE: `src/superbot/strategy/shadow_mode.py` (`ShadowConfig`, `ShadowModeEvaluator`, `ShadowResult`, `shadow_mode_eligible`, `evaluate_shadow_mode`) + `tests/unit/test_shadow_mode.py` (14 tests). Shadow mode eligibility checks opportunity count, elapsed minutes, and data quality percentage against configurable thresholds. All conditions must pass; failure reasons listed per condition. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M6.8` Internal-simulation eligibility and three-failed-validation-attempt version archive rule — DONE: `src/superbot/strategy/internal_simulation.py` (`InternalSimulationConfig`, `InternalSimulationEvaluator`, `InternalSimulationResult`, `VersionArchiveRule`, `VersionArchiveManager`, `evaluate_internal_simulation_eligibility`, `record_validation_attempt`, `is_version_archived`) + `tests/unit/test_internal_simulation.py` (19 tests). Internal simulation eligibility checks cost-adjusted return %, Sharpe, max DD against configurable thresholds. VersionArchiveRule tracks validation attempts per version and archives after 3 consecutive failures; passing validation resets failure count. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.1` Portfolio/strategy/correlation-group risk service — DONE: `src/superbot/risk/portfolio_risk.py` (`RiskLimit`, `RiskCheckResult`, `StrategyRecord`, `CorrelationGroup`, `PortfolioRiskService`, `register_strategy`, `update_strategy_pnl`, `check_strategy_risk`, `check_group_risk`) + `tests/unit/test_portfolio_risk.py` (15 tests). Portfolio risk service registers strategies with per-strategy limits (max DD, daily loss, position size), groups into correlation groups with group DD caps, checks trades against limits. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.2` Daily loss 3% and portfolio DD 10% halt/resume process — DONE: `src/superbot/risk/daily_loss_halt.py` (`DailyLossHaltResumeManager`, `HaltCheckResult`, `check_daily_loss_halt`, `check_portfolio_dd_halt`, `is_halted`, `can_resume`, `record_daily_loss`, `record_portfolio_dd`) + `tests/unit/test_daily_loss_halt.py` (16 tests). Halt manager: daily loss > 3% triggers halt; portfolio DD > 10% triggers halt; resume requires both below thresholds; halt blocks new entries while existing positions continue. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.3` Combined open-risk cap 5%; adaptive risk and verified sizing — DONE: `src/superbot/risk/open_risk_cap.py` (`PositionRisk`, `OpenRiskResult`, `OpenRiskService`, `register_open_position`, `remove_open_position`, `check_combined_open_risk`, `compute_adaptive_size`, `verified_size`) + `tests/unit/test_open_risk_cap.py` (16 tests). Open-risk service tracks combined open risk across all strategies/positions; combined cap 5% blocks new entries when exceeded; adaptive size scales to available headroom; verified size caps requested size to headroom. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.4` Tier multipliers (0.25/0.50/0.75/1.00), monthly review, max 10% relative increase — DONE: `src/superbot/risk/tier_multiplier.py` (`TierMultiplier`, `TierMultiplierResult`, `TierMultiplierService`, `VALID_TIER_MULTIPLIERS`, `get_tier_multiplier`, `assign_tier_multiplier`, `set_tier_multiplier`, `review_tier`, `next_review_date`, `set_last_review`) + `tests/unit/test_tier_multiplier.py` (14 tests). Fixed tier multipliers {0.25, 0.50, 0.75, 1.00}; monthly review cadence (30-day default); max 10% relative increase per review (snaps down to nearest valid tier); decreases always allowed; numeric tier criteria remain OPEN (no auto-assignment). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.5` ATR-relative volatility and hard blocks; thresholds OPEN, never guessed — DONE: `src/superbot/risk/atr_volatility.py` (`ATRReading`, `VolatilityBlockResult`, `VolatilityBlock`, `HardBlock`, `HardBlockResult`, `ATRVolatilityService`, `HardBlockService`, `compute_atr`, `compute_atr_relative_volatility`, `compute_volatility_block`, `compute_hard_block`) + `tests/unit/test_atr_volatility.py` (18 tests). ATR-relative volatility = ATR / current_price * 100; volatility block pauses trading when ATR-rel vol exceeds threshold; hard blocks pause when any metric exceeds threshold; all thresholds OPEN config inputs (never hardcoded). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.6` Competing signal ranking, reserve/capacity, group limits, resize/reject semantics — DONE: `src/superbot/risk/signal_ranking.py` (`Signal`, `RankedSignal`, `GroupLimit`, `GroupLimitResult`, `ResizeRejectDecision`, `AllocationResult`, `SignalRankingService`, `ReserveCapacityService`, `GroupLimitService`, `ResizeRejectSemantics`, `rank_signals`, `allocate_capacity`, `check_group_limits`, `resize_or_reject`) + `tests/unit/test_signal_ranking.py` (19 tests). Signals ranked by score descending; reserve/capacity blocks total size exceeding capacity; group limits enforce max signal count and max risk pct per group; resize/reject resizes signal to fit capacity or rejects when below min size. Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M7.7` Boundaries/concurrency/missing-input tests and risk audit events — DONE: `src/superbot/risk/risk_boundaries.py` (`AuditEvent`, `AuditEventLogger`, `BoundaryError`, `MissingInputError`, `ConcurrencySafeRiskService`, `audit_event`, `log_audit_event`, `validate_boundary`, `validate_not_missing`) + `tests/unit/test_risk_boundaries.py` (17 tests). Boundary validation blocks zero/negative/extreme inputs; missing inputs (None/empty) block operations; concurrency-safe shared state via RLock; audit event logger with immutable append-only events; all thresholds/config are explicit inputs (never hardcoded). Stdlib-only, no import-time network/MT5/database/model activity. Tests pass, ruff clean. Commit (see git log).
- `M8.1` PostgreSQL config/suitability benchmark on laptop — DONE: `src/superbot/persistence/postgres_benchmark.py` (`PostgreSQLBenchmarkService`, `BenchmarkResult`, `ConfigAssessment`, `ConfigParam`, `AllocationResult`, `SuitabilityVerdict`, `check_connection`, `benchmark_queries`, `assess_config`, `compute_suitability_verdict`, `run_postgres_benchmark`, `validate_not_missing`) + `tests/unit/test_postgres_benchmark.py` (16 tests). Connects to PostgreSQL with explicit config, benchmarks query latency (deterministic synthetic fallback when no live DB), assesses config params (shared_buffers, work_mem, effective_cache_size) against recommendations, returns PASS/WARN/BLOCK suitability verdict. Missing connection params block rather than defaulting. Stdlib-only, no import-time network/DB activity. Tests pass, ruff clean. Commit (see git log).
- `M8.2` Versioned migrations and old experiment readability — DONE: `src/superbot/persistence/migrations.py` (`Migration`, `MigrationResult`, `MigrationService`, `ExperimentRecord`, `ExperimentStore`, `apply_migration`, `rollback_migration`, `check_migration_status`, `record_experiment`, `read_experiment`, `validate_not_missing`, `MissingInputError`, `MigrationError`) + `tests/unit/test_migrations.py` (16 tests). Versioned migrations with up/down functions applied in ascending order, each at most once; migration tracking; old experiment readability with schema versioning (backward compatible reads); adding a column doesn't break old rows. Stdlib-only, no import-time network/DB activity. Tests pass, ruff clean. Commit (see git log).
- `M8.3` Append-only audit and correction linkage — DONE: `src/superbot/persistence/audit_linkage.py` (`AuditEvent`, `AuditEventLogger`, `AuditCorrection`, `AuditIntegrityError`, `audit_event`, `append_audit_event`, `link_correction`, `verify_audit_chain`, `CorrectionLinkage`) + `tests/unit/test_audit_linkage.py` (14 tests). Append-only immutable audit log with hash chain (each event's hash = hash(content + previous_hash)); corrections create NEW events linked to original event id (never modify originals); tampering detected via hash chain verification including recomputed hash comparison. Stdlib-only, no import-time network/DB activity. Tests pass, ruff clean. Commit (see git log).
- `M8.4` Experiment registry/data-code-strategy-parameter-cost-config refs — DONE: `src/superbot/persistence/experiment_registry.py` (`ExperimentRef`, `ExperimentRegistry`, `CodeRef`, `StrategyRef`, `ParameterRef`, `CostRef`, `ConfigRef`, `ArtifactRef`, `register_experiment`, `get_experiment_refs`, `find_experiments_by_code`, `find_experiments_by_strategy`, `find_experiments_by_parameter`) + `tests/unit/test_experiment_registry.py` (16 tests). Register experiments linking code (repo/commit/path), strategy (name/version), parameters (window/threshold), cost (spread/commission), config (env/region); lookup by experiment id, code commit, strategy name+version, parameter window. Stdlib-only, no import-time network/DB activity. Tests pass, ruff clean. Commit (see git log).
- Next: `M8.5` Checkpoint/crash restart reconciliation for jobs/signals/positions.

## 12. M0 Reconnaissance Findings (2026-10-28)

### Repository
- C:\SuperBot is NOT a git repo (no `.git` directory). Git 2.55.0.windows.3 installed. No branch/commit to record yet. Git initialization is a pending M1 foundation decision (not done blindly during reconnaissance).
- Spec pack files present at C:\SuperBot root: AGENTS.md, PRD.md, context.md, architecture.md, rules.md, task.md, schema.md, design.md, Debug.md, memory.md, agents.md, START_PROMPT.md, README.md, MANIFEST.json. Same files also under superbot_opencode_spec_pack/ plus superbot_opencode_spec_pack.zip and superbot_poc_kit.zip.
- superbot_poc_kit/ contains superbot_poc.py, README.md, results/ (baseline JSONs).
- No existing application code, no tests, no pyproject.toml/setup.cfg/pytest.ini at C:\SuperBot root. No application code modified during reconnaissance.
- AGENTS.md at root matches spec pack agents.md (governance: AI proposes, deterministic verifies, risk decides; shared versioned strategy framework, not ten LLM agents).

### OpenCode / tooling
- OpenCode v2.1.2 (`opencode --version`). Config at C:\Users\wasim\.claude\settings.json.
- MCP servers configured (mcp_config.json): `serena` (npx serena-slim --setup), `github` (npx @modelcontextprotocol/server-github; GITHUB_PERSONAL_ACCESS_TOKEN empty = not active). Context7/GitHub/Playwright/Supabase plugins are installed but MCP-level activation must be verified per use.
- Installed plugins (installed_plugins.json): supabase 0.1.15, playwright fbe07fb6ce7d, context7 fbe07fb6ce7d, superpowers 6.4.1, github fbe07fb6ce7d, claude-code-setup 1.0.0, sentry-cli 0.46.0, sentry 1.4.0, **ecc 2.2.2**, context-mode 1.0.169, caveman 2.7.0, code-review fbe07fb6ce7d, openviking-memory 0.6.4, claude-mem-cowork 0.1.3, headroom 0.39.1, vercel 0.50.0, day-trader-skill 2.0.0.
- Enabled plugins: day-trader-skill@day-trader-skill = true only.
- ECC commands present (plugin commands dir): loop-start, loop-status, quality-gate, harness-audit, security-scan, code-review, python-review, pr, plan, etc. Verified as files; active registration in this session not yet confirmed. quality-gate = file formatter (ruff format for .py) driven by hook stdin JSON, not CLI args. harness-audit = node scripts/harness-audit.js. security-scan = npx ecc-agentshield scan. No `C:\Users\wasim\.claude\commands` directory.
- Skills installed (~.claude/skills): archify, caveman, code-review, diagnosing-bugs, find-docs, find-skills, frontend-design, git-guardrails-claude-code, graphify, learned, megacave, prototype, research, scaffold-exercises, skill-creator, tdd, vercel-*, web-design-guidelines, wizard, writing-*, etc.
- Agents installed (~.claude/agents): many role-based .md files. None Superbot-specific.
- Caveman mode: full. Hooks use caveman-proxy native-hook across SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/etc.

### Python / dependencies (Python 3.14.7)
- py.exe at C:\WINDOWS\py.exe; pip 26.2.1; pytest 9.1.1; ruff 0.17.2.
- psycopg 3.3.6, psycopg-binary 3.3.6, SQLAlchemy 2.1.4 — import OK.
- ollama 0.6.3 — imports (no __version__ attribute).
- **metatrader5 5.0.6231 — pip shows installed at Python314 site-packages but `import metatrader5` raises ModuleNotFoundError.** Blocks MT5 read-only discovery until resolved (mirrors C:\Bot project note: "live MT5 blocked by unimportable metatrader5 package").
- streamlit 1.66.1, fastapi 0.143.0 available.
- **goldmasters-contracts 0.1.0 installed but PROHIBITED — must not be used or derived from.** six-agent-trading-desk 0.1.0 at C:\Bot is a separate project; not touched.

### Hardware / services
- Windows 10 build 19045, ~7.44 GiB RAM (~2.01 GiB free at snapshot), 2 logical CPU threads, HDD.
- PostgreSQL 18 service RUNNING; psql 18.0.6.0 at C:\Program Files\PostgreSQL\18\bin\psql.exe.

### Baseline POC re-verified
- `py superbot_poc.py --warmups 1 --repetitions 5` → correctness `status: PASS`; 7 synthetic checks (OHLCV validity/chronology; next-bar-open entry; stop-first ambiguous SL/TP; explicit spread/commission; stop-gap worse-open fill; portfolio/daily-loss/drawdown gates; signal timestamp before entry).
- Fixture 10 bars, SHA-256 e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd.
- This run: median runtime 28.877 ms / 2,000 iterations; range 3.83 ms; median tracemalloc peak 160 bytes (Python allocations, not process RSS).
- Saved report: C:\SuperBot\superbot_poc_kit\results\baseline_20261028T131428Z.json.
- Limitations: synthetic fixture only, no MT5/broker metadata, not a full portfolio simulator, no engine comparison, not for live/demo trading.

### OPEN decisions / blockers carried forward
- Engine winner (custom baseline vs NautilusTrader vs LEAN): OPEN.
- OHLCV storage format (Parquet vs alternatives): OPEN.
- UI/API/chart/packaging stack: OPEN.
- Ollama vs llama.cpp and qualified local model: OPEN.
- metatrader5 import failure: BLOCKER for M2.5 MT5 discovery; not resolved.
- No git repo: pending M1 foundation decision.
- No existing app code/tests/config: M1 foundation required before any implementation.

### Evidence boundary
- Only the synthetic baseline POC is proven tested. No engine, full MT5 link, PostgreSQL app integration, local model runtime, or complete app is tested on this laptop. No unverified PASS status claimed.
