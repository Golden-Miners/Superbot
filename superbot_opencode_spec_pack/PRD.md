# Superbot — Product Requirements Document

**Status:** Baseline requirements from user-confirmed decisions. Implementation choices marked **OPEN** must not be silently inferred. Product is a new standalone project, not a GoldMasters fork.  
**Principle:** **AI proposes. Deterministic code verifies. Risk limits decide.**

## 1. Purpose and outcomes

Build a local-first multi-agent quantitative research workstation that ingests permitted market data, researches explicit strategies, runs historical tests, validates candidates on chronological out-of-sample (OOS) data, manages internal simulations, records every decision, and supports bounded evidence-based strategy improvement. It must explain why a candidate passed, failed or was blocked.

This is not a profit promise. Backtest results do not prove future profitability. The uploaded *Ultimate AI Algo Trading Playbook* is process inspiration for testable rules, causal simulation, trial accounting, versioning, rollback and self-improvement; its synthetic examples do not prove market edge.

Product outcomes:
1. Reliable, reproducible OHLCV pipeline for the agreed asset/timeframe universe.
2. Explicit, machine-testable strategy rules with deterministic entries, exits and invalidation.
3. Deterministic event-driven simulation with conservative OHLCV ambiguity handling, costs and verified instrument constraints.
4. Chronological validation, walk-forward analysis, robustness and trial accounting that block weak/leaky candidates.
5. Deterministic risk service that blocks entries regardless of model or agent output.
6. Specialist agents coordinated by a deterministic orchestrator, using versioned schemas and evidence.
7. Internal simulation, job scheduling, searchable experiments, backup/recovery, monitoring and quant-terminal dashboard.
8. Controlled self-improvement that never self-authorizes live trading.

## 2. V1 universe and operating boundary

**Instruments:** Gold, Silver, Bitcoin, Ethereum, US Oil.  
**Timeframes:** M5, M15, H1, H4.

Architecture supports multiple assets even where a feed does not cover all symbols. Discover and verify actual XM MT5 Market Watch symbols and metadata; never assume symbol names, contract sizes, hours, tick values or volume steps.

- Initial provider: XM MT5, read-only market data and read-only account balance/spec discovery where available. Any access requires explicit local setup.
- Supplementary native crypto exchange data only if a required dataset is unavailable from the approved source and the alternative is explicitly recorded.
- Python-first, local-first, Windows-native deployment.
- First target: Windows 10 Lenovo laptop, approximately 8 GB RAM and 2 logical CPU threads. Later target: Windows 10 desktop, approximately 12 GB RAM. Hardware details are in `context.md`.
- Local AI only; hosted inference budget is ₹0; English-only.
- App runs while the computer/app runs; 24/7 uptime is not required.
- **Local PostgreSQL** is selected for application records. OHLCV storage format remains OPEN pending benchmark of Parquet and alternatives.
- V1 is research, signals, historical testing and internal simulation only. No live-order path. MT5 demo readiness is future scope behind explicit named human approval and is not authorized by this prompt.

## 3. User experience

A modern quant-terminal dashboard with graphite/dark base, cyan/teal accents, balanced information density and clear states. It shows:

- Market status, symbols/timeframes, data freshness/coverage and source identity.
- Research queue, running/paused/failed jobs, resource load and model/runtime health.
- Strategy/version lifecycle, signal proposals, validation metrics/windows and failure reasons.
- Portfolio exposure, per-strategy/correlation-group risk, simulated positions, stops and P&L.
- Data quality, broker metadata freshness, audit integrity, backup/restore status and critical alerts.
- Searchable/exportable experiment history referencing dataset, code, parameters, validation configuration and outputs.
- Controls to start/pause/resume/cancel research jobs; enable/disable strategy versions; edit approved settings; inspect logs/reports.

Dashboard sessions must be authenticated and role-limited. Bind locally by default. Remote access, if enabled, uses a private VPN such as Tailscale, never direct public exposure. UI/API framework, charting library and packaging method remain OPEN pending repository/environment inspection and an ADR.

## 4. Workflow and lifecycle

1. Discover providers/symbols and verify source metadata/time boundaries.
2. Ingest OHLCV and validate gaps, duplicates, suspicious prices, staleness and coverage.
3. Run deterministic baselines and AI-proposed candidates in isolated research jobs.
4. Validate rule schemas and causal/time ordering.
5. Run fast exploratory research plus the primary event-driven simulator.
6. Run chronological train/validation/untouched-test separation, at least 3 walk-forward windows, OOS checks, neighboring-parameter robustness, cost stress and leakage checks.
7. Compare no-trade baseline, simple deterministic baseline and previous approved version when available.
8. Passing candidates enter shadow mode with configurable opportunity count, elapsed duration and data-quality conditions.
9. Eligible candidates may automatically enter **internal simulation** after deterministic gates pass. This does not authorize external orders.
10. Monitor active simulations hourly and check risk/integrity immediately on relevant events.
11. Observe outcomes; diagnose failures; propose one bounded change; count the trial; re-run the required validation lifecycle; preserve/reject/archive/rollback under deterministic rules.
12. A future demo-readiness stage requires realistic costs, all gates and explicit human approval. It is not part of present authorization.

## 5. Strategy requirements

Initial reference strategies:
1. Trend-following and pullback.
2. Liquidity sweep and market structure. BOS/CHOCH only with explicit definitions. Order blocks/FVG only when precise, testable rules have been agreed; ambiguous discretionary labels are not executable rules.
3. Quantitative/statistical strategy.

Use a shared framework with separately versioned strategy implementations/configurations. Do not create one separate LLM agent per strategy just because an earlier idea mentioned ten strategy agents. Support strategy families architecturally, but phase implementation and fully validate these three first.

Each strategy must specify inputs, entries, exits, stop/invalidation, expiry, max holding period or explicit none, reversal behavior, trailing/partial-exit rules where used, parameter bounds/units and version. AI may propose rules or rank/filter signals; it cannot bypass schema validation/risk gates or write official state.

## 6. Validation gates

Binding selected criteria unless the user changes them through a recorded decision:

- Normal minimum of 100 completed OOS trades. Low-frequency strategies may require more elapsed time, but the evidence bar must not be silently lowered.
- At least 3 chronological walk-forward windows.
- OOS profit factor >= 1.20.
- OOS Sharpe >= 1.0 and Sortino >= 1.5.
- Strategy-level OOS maximum drawdown <= 15%.
- At least 2 of 3 walk-forward windows have positive net returns; every window stays within drawdown limits.
- Positive OOS net returns after available estimated costs before internal-simulation promotion; disclose unavailable components.
- Include available spread, commission, swap/funding and slippage estimates. A 2x cost stress test is mandatory before any future demo readiness.
- Neighboring parameter values must show a stable performance region, not a single isolated peak.
- Point-in-time data/features and automated leakage checks are mandatory; detected leakage fails a candidate.
- Count every trial; reserve an untouched final evaluation period; apply multiple-testing controls where feasible.
- Robustness failure blocks promotion and is preserved. Changed versions restart applicable validation.
- Balanced scorecard: returns, drawdown, risk-adjusted performance, trade count and robustness.

**OPEN:** annualization convention/risk-free rate; numerical definition of a stable parameter region; sample-count/elapsed thresholds per risk tier; deterioration thresholds. Until resolved, expose the convention/config and do not silently treat one metric definition as canonical.

## 7. Risk and portfolio controls

All applicable portfolio-wide, strategy-level and correlation-group checks must pass. AI cannot override them.

Selected limits:
- Combined open risk cap: 5%.
- Daily loss limit: 3% of starting daily equity.
- Portfolio drawdown halt: 10% from relevant equity peak; pause all new entries and require human-approved resume after checks pass.
- Adaptive strategy-specific per-trade risk below a configurable central cap; exact cap/floors remain OPEN.
- Four evidence tiers with base-risk multipliers 0.25x, 0.50x, 0.75x and 1.00x. Tier moves require configured trade count, elapsed time, passing metrics and robustness.
- Maximum 10% **relative** risk increase per monthly review, not percentage points; minimum new evidence required.
- Use ATR relative to price for volatility. Reduce risk as volatility rises inside configured bounds; block new entries above configured maximum or when measurement is unreliable.
- Size from cash risk budget, stop distance and verified broker volume/tick/contract specs. If a required input is unverifiable, block entry.
- Shared correlation-group budgets and configurable strategy/group concentration caps.
- Rank competing signals deterministically by evidence tier, signal quality, expected risk-adjusted return and correlation impact; tie-break on lower risk-capacity use. Resize if feasible under lot/strategy constraints, else reject.
- Daily/portfolio breach pauses new entries and alerts. Existing simulated positions continue management under defined stops/exits. Portfolio DD halt requires human-approved resume.

**OPEN:** volatility thresholds/floors/ceilings; correlation estimator/window/groups; tier trade counts/durations; deterioration threshold; central and weaker-tier per-trade caps; starting daily equity definition and daily-loss recovery procedure. Do not invent these values. Block affected entries until required configuration is defined and validated.

## 8. Data correctness

- Preserve source identity/source timestamps; store canonical timestamps in UTC and retain verified XM server-time metadata/candle boundaries.
- Discover symbols/specs from MT5; confirm ambiguous mappings.
- Historical backfills plus incremental refresh while connected.
- Track actual coverage per symbol/timeframe; do not assume uniform history.
- Flag gaps, duplicates, suspicious prices and source disagreement; exclude affected periods from validation until resolved.
- Provider outage, stale data or disagreement pauses affected work; never silently merge providers.
- OHLCV cannot resolve all intrabar execution ordering; simulator must use conservative assumptions.

## 9. Simulator and fills

- Event-driven simulator is primary validation; fast sweeps are exploratory only.
- Market order fills at next candle open, adjusted for modeled spread/slippage.
- If SL and TP both touch in one candle and order is unknown, assume SL first.
- Stop gaps fill at worse opening price plus applicable costs.
- Limit orders use conservative fill rules with configurable trade-through buffer.
- Contract size, tick size/value, min/max/step volume, trading constraints and sessions require fresh verified specifications; missing/stale values block affected simulation.
- Break-even applies only when defined in the strategy version. Trailing rules are strategy-specific and deterministic.
- Support partial take-profit only within verified volume constraints; record each partial exit/stop adjustment as a separate event.
- Max holding period is strategy-specific or explicitly none.
- Opposite signals use a versioned strategy-specific reverse/exit/ignore rule.
- Signals need strategy-specific expiry and invalidation; stable signal identity/dedup protects against duplicates.
- Multiple strategies may hold one instrument only if individual and aggregate risk limits pass.
- If data is stale before entry, retain a pending signal only if policy/validity allow; after data resumes, revalidate. Do not enter simply because data resumed.

## 10. Scheduling and resource management

- Configurable local intervals run only while app is running; prevent overlapping duplicate jobs and define missed-run behavior per job.
- Priority order: integrity/recovery; critical health checks; scheduled validation; routine research; exploratory work.
- Adapt concurrency to measured CPU/RAM/disk/model load, hard ceilings and reserved critical-service capacity.
- Under pressure defer/pause interruptible lower-priority tasks and checkpoint where possible. Protect data integrity, risk checks and simulated-position management.
- Waiting jobs may gradually gain priority but never outrank safety/recovery/critical tasks.
- Dynamic model selection considers task quality, schema correctness, repeatability, latency, RAM requirement and system load. If no qualified model fits, skip AI-dependent work and mark incomplete.
- Benchmark Ollama vs llama.cpp on both devices; do not preselect model/runtime.

## 11. Persistence, audit and backup

- Local PostgreSQL for application records; benchmark OHLCV format before selecting. Preserve original data and separately version cleaned/derived data.
- Store searchable experiment metadata/events/summaries in DB; large outputs/datasets in versioned files with immutable references/hashes.
- Each run records dataset/source hash, code/strategy version, parameters, validation config, costs, seeds where relevant, outputs, trial count, timestamps, environment/commit and failure reasons.
- Append-only audit events. Corrections are new events linked to originals; never silently edit/delete evidence.
- Full simulated trade lifecycle audit: signal inputs, checks, sizing, fills, costs, stop changes, partials, final P&L and rejection reasons.
- Audit integrity failure invalidates affected experiment, blocks promotion, alerts and preserves remaining evidence.
- Daily local plus encrypted cloud backup, 30-day retention, integrity verification and monthly restore test. No credentials in ordinary config/backups. Cloud provider/key-management/bandwidth remain OPEN.
- Disk pressure: verified regenerable cache/temp cleanup first; then pause storage-intensive jobs; preserve original data, audit and simulation state.
- Crash/restart must reconcile jobs, simulated positions and pending signals. Resume only after integrity checks.
- Document laptop-to-desktop migration with config, DB backup, data manifests/checksums, dependency/model reinstall and environment revalidation.

## 12. AI and agent governance

- Deterministic workflow orchestrator coordinates specialist agents.
- Versioned structured schemas validated at every handoff.
- Agents use scoped read-only data. Role-based permissions; broader research access is not write authority.
- Only deterministic services write official strategy versions, experiment records, risk settings and lifecycle state. Agents submit proposals.
- AI claims remain unverified without evidence; preserve evidence-linked approved knowledge only.
- Repeat high-impact tasks within configured limits; unresolved conflicts are marked and block dependent decisions.
- Model/runtime/quantization/config change is a new candidate requiring task-specific qualification.
- Model failure: bounded retries, schema/semantic validation, qualified fallback if safe; otherwise skip and mark incomplete. Never bypass risk controls.
- News/sentiment are later-phase free permitted APIs/RSS. Record source, publication time, instrument, category, sentiment, confidence and supporting text. Missing/stale news blocks news-dependent decisions only; technical work can continue. News never overrides risk/orders.

## 13. Self-improvement lifecycle

Lifecycle: research/basic verification → historical OOS/walk-forward/robustness → shadow mode → internal simulation → future demo readiness (human approval only). Every strategy/parameter/risk-rule change restarts required validation. After three failed validation attempts, disable/archive that version and preserve records. Material change creates a new version. “Failed validation attempts” are not losing trades.

Loop: observe baseline decisions/fills/results → diagnose failure class (data, strategy, execution model, risk, runtime, operations) → propose one bounded falsifiable change → count trial and validate schema → run regression/full applicable gates → advance eligible version only to internal simulation → monitor and roll back to known-good on violation. Never self-authorize live trading.

## 14. Security, operators and release

- Protected local credential storage; redact secrets from logs/exports; no hard-coded credentials; secrets never enter source control, Supabase or ordinary backup.
- Authenticated dashboard, private VPN if remote, no public exposure.
- Profiles: `research`, `internal-simulation`, future guarded `demo-readiness`; version changes with actor/reason, retain last-known-good. Invalid settings are rejected.
- Only authorized owner may change sensitive settings. No live execution path in this scope.
- Mandatory tests: unit, integration, end-to-end, data-quality, simulator, risk controls, failure recovery, audit integrity, backup/restore, config migration and UI/browser tests as applicable.
- Release requires all mandatory tests passing, verified risk/audit controls, tested recovery, no unresolved critical/high defects and explicit human release approval. Report skipped tests as skipped/blocked, never passed.

## 15. OPEN decisions

Current register is in `context.md`: engine winner, market-history format, UI/API/chart/packaging stack, local model/runtime, tier/volatility/correlation thresholds, metric conventions, missing cost assumptions, cloud backup/key management and other numeric policies. Resolve by evidence and ADRs. Build safe isolated contracts/tests in parallel where possible; never guess values just to remove a blocker.
