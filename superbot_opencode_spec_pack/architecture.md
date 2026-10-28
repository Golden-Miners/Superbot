# Superbot — Target Architecture

**Status:** Component boundaries are defined. Engine/runtime/UI/storage details marked OPEN require evidence and an ADR. This document does not claim the app already exists.

## 1. Principles

- Local-first, Python-first modular app with local UI and background workers.
- Deterministic workflows/state transitions; specialist LLMs are replaceable and subordinate to deterministic domain services.
- Explicit interfaces/adapters for market data, simulation engine, models, storage, charting and news.
- Reproducible experiments; append-only audit; versioned schemas, datasets and strategies; rollback.
- Safety, data integrity and current simulated-position management outrank exploratory AI/backtests.
- No live execution path in current scope.
- External repositories are candidates, not architectural authorities; keep only after equivalent tests/integration evidence.

## 2. Logical component map

```text
Local Dashboard / Operator API
          |
Authentication + Config/Command Validation
          |
Application Services / Job API
          |
Deterministic Workflow Orchestrator + Scheduler + Supervisor
    |         |            |             |
Data       Strategy      Research/AI   Validation & Lifecycle
Pipeline   Registry      Agents        Gates
    |         |            |             |
Provider    Rule Schema   Qualified     Event-driven Simulator
Adapters    Validator     Local Model   + Conservative Fill Model
    |                      Runtime              |
XM MT5 read-only                            Deterministic Portfolio/Risk
(and explicitly approved sources)                |
    |                                           |
Canonical OHLCV / Dataset Registry          Simulated Positions/Ledger
    |                                           |
Versioned file store (format TBD) + Local PostgreSQL application database
                     |
Audit, Experiment Registry, Backup/Restore, Metrics/Logs/Alerts
```

This does not preselect UI framework or engine. Keep interfaces stable while candidates are tested.

## 3. Modules and ownership

Conceptual boundaries only; choose package layout after repo reconnaissance and record an ADR.

- **Bootstrap/supervisor:** startup/shutdown ordering, health, worker lifecycle, graceful restart, config validation.
- **Contracts/domain:** versioned records/state enums for bars, instruments, candidates, validation, signals, fills, risk and audit.
- **Provider adapters:** XM MT5 read-only source, symbol/spec discovery, approved supplementary source adapters. No strategy or risk logic.
- **Data ingest/quality:** backfill/incremental refresh, UTC normalization, coverage, gaps/duplicates/suspicious bars, staleness and lineage.
- **Dataset registry/storage:** immutable source data, separately versioned cleaned/derived datasets, manifest/hash and storage benchmark interface.
- **Strategy registry/executor:** versioned rules, parameters, causality, expiry, invalidation, signal identity; AI proposals staged separately.
- **Research:** deterministic baselines, fast sweeps, trial count and candidate generation.
- **Simulation adapter:** common protocol for custom baseline/candidate engine; event/fill/accounting contracts; costs and conservative OHLCV policy.
- **Risk service:** independent deterministic gates/sizing, callable with no model.
- **Validation:** chronological splits, OOS, walk-forward, leakage, baselines, robustness, costs/stress and scorecards.
- **Agent orchestrator:** roles, graph, schema validation, qualified model routing, bounded retries and evidence.
- **Lifecycle/version store:** candidate staging, gate state, promotion eligibility, known-good version, archive/rollback.
- **Simulation ledger:** positions, fills, cash/equity, costs, stops, partial exits, exposure, reconciliation.
- **Experiment/audit service:** append-only events, immutable references and reproducibility checks.
- **Scheduler/resource manager:** priorities, checkpoint, cancellation, dedup, adaptive concurrency and missed-run policy.
- **Observability:** structured logs/metrics/alerts and data/model/API/MT5 health.
- **Backup/restore/migration:** daily backup, encryption, 30-day retention, integrity verification, monthly restore test, laptop→desktop procedure.
- **Dashboard/UI:** local quant terminal, private authenticated route, no public exposure.
- **News/sentiment (later):** free-source ingestion and context only.

## 4. Event and authority flow

1. Provider returns source-stamped bars/spec metadata.
2. Data-quality service validates source, timestamps, freshness, gaps and specs.
3. Strategy rules use point-in-time features to create versioned signals.
4. Deterministic schema/causality validator checks proposal.
5. Signal enters queue with stable identity, expiry and invalidation.
6. Risk service checks portfolio/strategy/correlation limits and verified specs.
7. Simulator applies conservative fills/costs; records entries, costs, stops, partials and closes separately.
8. Validation evaluates OOS/walk-forward/robustness and trial accounting.
9. Deterministic lifecycle state machine blocks, preserves, archives or advances candidate.
10. AI analyst/reviewer summarizes evidence/classifies failures/proposes bounded changes but cannot write official state.
11. Audit records every decision and evidence link; dashboard shows state/blockers.

## 5. State machines

Use explicit enums and checked transitions, not loose status strings.

Suggested job states: `queued`, `validating_inputs`, `running`, `checkpointed`, `pause_requested`, `paused`, `cancel_requested`, `cancelled`, `succeeded`, `failed`, `blocked`, `interrupted`, `recovery_required`.

Suggested strategy lifecycle: `proposed`, `schema_rejected`, `research`, `historical_validation`, `shadow`, `internal_simulation`, `disabled`, `archived`, `blocked`. Future demo readiness is separately guarded. Names may change by ADR but remain explicit and tested.

Every state transition records actor/service, prior/new state, reason, UTC timestamp, run/correlation ID and evidence references. Writes should be transactional/idempotent where required.

## 6. Persistence boundaries

### Local PostgreSQL — selected for application records

Store searchable and transactional metadata/state: jobs, strategies/versions, configs, validation metrics, signals, simulation-ledger records/events, lifecycle transitions, audit metadata, experiment summaries and backup manifests. Migrations are versioned and old experiments remain interpretable.

### Market-history store — OPEN

Benchmark Parquet and reasonable alternatives for compression, query/read speed, incremental updates, partitioning by source/symbol/timeframe/date, crash recovery and actual HDD/8-GB resource use. Preserve immutable acquired data; store cleaned/derived data separately with provenance. Decide by measured evidence, not familiarity.

### Large artifacts

Store as versioned files; PostgreSQL stores content hash, schema/version refs, dataset/strategy/code/config refs and location. Paths must be portable across computers, not temporary-directory-only.

### Backup

Daily local plus encrypted cloud, 30-day retention, integrity checks and monthly restore test. Cloud destination, key management, bandwidth and capacity remain OPEN. Never back up broker secrets.

## 7. Data/time design

- Store canonical timestamps in UTC; preserve source timestamps and original timezone/offset and broker time metadata.
- Verify XM server timezone; do not assume India time or UTC is broker time.
- Canonical instrument identity is separate from provider symbol spelling. Mapping includes provider, raw symbol, normalized instrument, source/time and verification status.
- Canonical bar key includes provider, instrument/mapping version, timeframe and UTC open time; duplicate semantics need documenting.
- Validate candle alignment, gaps against session/calendar metadata, scheduled closures and suspicious outliers.
- Keep provider data separate; no silent merge.
- Feature generation carries availability time; no future-known value can appear at an earlier signal timestamp.

## 8. Simulator contract

Candidate engines must share an adapter capable of equivalent fixtures, strategy rules, costs and tests: data feed, callbacks/events, market/limit/stop simulation, fills, portfolio state, costs, event timeline, deterministic configuration/seeds, metrics/output events and checkpoint/replay where available.

Custom simulator is a reference control, not automatically the winner. First candidates are NautilusTrader and QuantConnect LEAN. Keep Superbot risk gates authoritative even if engine has its own risk/execution logic.

Required semantics: next-bar-open market fills plus spread/slippage; stop-first ambiguous same-bar SL/TP; worse-open stop gap; conservative limit trade-through; verified tick/contract/volume constraints; explicit costs; distinct stop/partial events; strategy-specific break-even/trailing/max-hold/reversal; no look-ahead.

## 9. Local AI routing

Benchmark Ollama vs llama.cpp on both devices. Task fixtures evaluate correctness, schema validity, repeatability, latency, task quality vs reviewed reference, total process memory and system impact. A model name alone is not evidence of quality.

Router considers task type, qualified quality, free RAM, latency, CPU/GPU capability, load and concurrency. If no qualified model fits, use safe deterministic fallback or skip/mark incomplete. Changed model version/quantization/runtime is a new qualification candidate.

Resource priority: integrity/recovery/critical health; risk/data services and simulated position management; scheduled validation; routine research; exploratory sweeps. Under pressure, checkpoint/pause low-priority interruptible work.

## 10. Dashboard/API and remote access

Expose operations through validated local services/API. UI must not write DB tables directly. Authenticate sessions and authorize sensitive controls in backend. Bind locally by default. Optional remote access uses a private VPN; never expose unauthenticated public endpoints. No live-order controls.

UI framework, API framework, authentication/session method, chart library and packaging are OPEN until repo/env inspection and a resource-tested ADR. `tradingview/lightweight-charts` may be evaluated; verify current API/version/attribution. Do not imply integration before it exists.

## 11. Repositories and adoption posture

User says licensing for previously considered repositories is clear as of 2026-10-28. Still record exact adopted version/license/attribution and assess current compatibility, tests, maintenance and dependencies. None is automatically a required dependency.

- `nautechsystems/nautilus_trader`: first event-driven engine POC.
- `QuantConnect/Lean`: first event-driven engine POC.
- Custom Python event-driven baseline: control for differential correctness.
- `StockSharp/StockSharp`: evaluate only for a necessary broker/data capability if C# integration is justified.
- `TauricResearch/TradingAgents`: agent-graph/handoff patterns; not risk authority.
- `AI4Finance-Foundation/FinRobot`: optional agent/research capability candidate.
- `microsoft/qlib`: optional quant research/ML component.
- `AI4Finance-Foundation/FinRL`, `tensortrade-org/tensortrade`: later RL only if justified/resource-tested.
- `Lumiwealth/lumibot`: alternative framework candidate; compare, do not stack frameworks by default.
- `mementum/backtrader`: reference/alternative only if it proves useful.
- `polakowo/vectorbt`: possible fast sweeps, not sole authoritative event-driven validator.
- `shiyu-coder/Kronos`: optional future forecasting experiment, not core engine.
- `virattt/ai-hedge-fund`: educational/reference patterns unless a specific component proves useful.
- `aayxshkumar/ai-hedge-fund`: unaudited fork; no wholesale import without unique justification/source review.
- `tradingview/lightweight-charts`: optional chart renderer with attribution recorded.

For every evaluated component record official URL, inspected version/commit, license, runtime, requirements, suitability, tests/benchmark, adopted paths and accept/reject reason. If only patterns were used, record that, not a dependency integration.

## 12. Engine proof of concept and scoring

Identical fixtures/strategy/cost/split settings for: (1) custom Python baseline; (2) NautilusTrader; (3) LEAN. Correctness gates run first. Use a small correctness fixture, representative historical dataset and larger stress set only if laptop capacity allows. Measure event correctness, runtime, full-process-tree peak RSS/working set, CPU, disk I/O, throughput, startup, failure rate, repeatability and impact on critical services. Isolated environments, pinned deps, no real credentials.

Weights: safety/correctness 30%; compatibility 20%; reproducibility 15%; resource efficiency 15%; maintainability 10%; performance 10%. Hard disqualifiers: mandatory correctness failure, inability to enforce deterministic Superbot risk controls, unresolved critical security defect, or incompatible licence/terms. Winner must score >=80/100, pass every mandatory gate and have no unresolved critical integration risk. Do not score before comparable test data exists.

## 13. Standardized POC protocol (questionnaire defaults)

Use these defaults for candidate-engine and storage/runtime comparisons unless a test harness proves a different sampling plan is needed. Record any deviation as a measured reason, not a silent assumption.

- **Metrics:** runtime, process-tree peak RAM/RSS or working set, CPU time, disk I/O, throughput, startup latency, failure rate, repeatability and impact on critical services. Separate correctness testing from performance/resource measurement.
- **Repetitions:** one warm-up plus five measured repetitions as the initial standard. If results are noisy under a defined noise rule, perform additional repetitions and record why; define the noise rule in the harness before viewing results.
- **Dataset sizes:** small fixed correctness fixture; representative historical OHLCV workload; larger stress workload only if available laptop RAM/disk budget permits. Never let the stress dataset harm critical services. Record dataset hash, provenance, bar count and coverage.
- **Correctness:** strict gate before performance ranking—known fixtures; exact trade/event accounting; next-open rules; stop-first ambiguity; adverse gap logic; configured costs; risk controls; temporal causality/no look-ahead; deterministic repeatability. A correctness failure disqualifies the candidate regardless of speed.
- **Evidence retention:** keep configs, dataset hashes/manifests, repository commits, dependency lockfiles, machine/OS/hardware facts, command lines, logs, raw outputs, test results, limitations and scoring workbook/report. Results must be reproducible and comparable.
- **Isolation:** separate pinned environments; no broker credentials, real account mutation or order submission. Use synthetic fixtures first and explicitly approved historical market data for the representative workload.

## 14. Deployment topology

- Native Windows install; packaging method OPEN.
- Supervisor monitors API, workers, PostgreSQL and model runtime.
- Start on demand; explicit operator action starts scheduled research.
- Graceful shutdown stops new jobs, checkpoints/finishes interruptible work, persists, reconciles and exits.
- Migration package: non-secret config, DB backup, dataset manifests/checksums, artifact refs, dependency locks and revalidation checklist.
- Desktop migration requires reinstall/revalidation of deps/models; do not assume byte-identical environment.
