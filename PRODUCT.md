# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Solo quantitative researcher / trader working from a home Windows laptop (~7.44 GiB RAM, 2 logical CPU threads, Windows 10 build 19045, HDD); later target is a Windows 10 desktop (~12 GiB RAM). Their job is personal strategy research: researching strategy ideas (trend/pullback, liquidity-sweep/market-structure BOS-CHOCH, quantitative/statistical), running backtests on historical OHLCV, validating candidates through chronological walk-forward and out-of-sample gates, and monitoring internal simulations — all without live execution in V1.

## Product Purpose

Superbot is a standalone, local-first AI trading research, backtesting and internal-simulation application. It ingests permitted market data, researches explicit strategies, runs historical tests, validates candidates on chronological out-of-sample data, manages internal simulations, records every decision, and supports bounded evidence-based strategy improvement. It must explain why a candidate passed, failed or was blocked. Success means reproducible, deterministic research with verifiable gates — not profit; backtest results do not prove future profitability.

## Positioning

AI proposes, deterministic code verifies, risk limits decide. Specialist agents (analyst, strategy proposer, reviewer, diagnostic) are advisory and submit proposals only; a deterministic orchestrator and deterministic risk/validation services own lifecycle state, official strategy versions, experiment records and risk configuration. Local AI only with a ₹0 hosted-inference budget, English-only. MT5 access is read-only and setup-gated; no live order path exists in V1 and none is authorized.

## Operating Context

Runs while the computer/app runs; 24/7 uptime is not required. Python-first, Windows-native deployment on a local-first stack: Python 3.14.7, FastAPI + uvicorn API, Streamlit quant-terminal dashboard, Plotly charts, local PostgreSQL 18 for application records, Parquet (zstd) for OHLCV history (ADR-002), pip packaging. Stack confirmed by the existing codebase (pyproject.toml) and ADR-004 (docs/adr/0004-ui-api-chart-stack.md); task.md M11.1–M11.2 recorded DONE. Dashboard binds localhost only; remote access, if ever enabled, uses a private VPN such as Tailscale, never direct public exposure. MT5 read-only discovery/feed connects to a real XM MT5 terminal (XMGlobal-MT5 17, account 420764750) only after explicit local setup; no order submission methods exist. V1 instruments: Gold, Silver, Bitcoin, Ethereum, US Oil × M5/M15/H1/H4, with actual symbol/metadata discovery required — symbol names, contract sizes, hours, tick values and volume steps are never assumed.

## Capabilities and Constraints

Confirmed functionality:
- Reproducible OHLCV pipeline for the V1 universe with source identity, UTC canonical timestamps, gap/duplicate/suspicious/stale detection and per-symbol/timeframe coverage tracking.
- Versioned, machine-testable strategy rules with deterministic entries, exits and invalidation; shared framework with separately versioned strategy implementations/configurations — not one LLM agent per strategy.
- Deterministic event-driven simulator as primary validation (next-bar-open fills, stop-first ambiguous SL/TP, conservative stop-gap and limit fills, explicit costs, verified tick/contract/volume constraints; missing/stale specs block operation).
- Chronological train/validation/untouched-test split, >=3 walk-forward windows, OOS metrics, parameter-neighbor robustness, cost-adjusted metrics, 2x cost stress, leakage checks, trial counting and multiple-testing controls.
- Binding validation gates: OOS PF >= 1.20, Sharpe >= 1.0, Sortino >= 1.5, strategy OOS max DD <= 15%, >=2 of 3 walk-forward windows positive, every window within DD limit, >=100 completed OOS trades normal minimum.
- Deterministic risk service: combined open-risk cap 5%, daily loss limit 3%, portfolio DD halt 10% with human-approved resume, four evidence tiers (0.25x/0.50x/0.75x/1.00x), ATR-relative volatility, correlation-group budgets, deterministic competing-signal ranking with resize-or-reject.
- Internal simulation after deterministic gates pass (never authorizes external orders); three failed validation attempts disable/archive a version; evidence preserved.
- Searchable experiment registry, append-only hash-chained audit with correction linkage, scheduled jobs only while app runs, crash/restart reconciliation, local + encrypted cloud backup with 30-day retention, integrity checks and monthly restore test.
- Authenticated, role-limited dashboard (research / internal-simulation profiles; demo-readiness guarded, not a V1 profile); secrets redacted, never stored in config/source control/backups.

Technical constraints:
- Local AI only; hosted inference budget ₹0; English only.
- No live trading/live broker order submission or execution path in this scope; MT5 strictly read-only.
- No public dashboard binding; localhost by default.
- Deterministic services write official state; agents cannot override risk gates or write official strategy versions, experiment pass/fail, or lifecycle promotion.
- Missing or unverifiable required inputs block affected operations; never silently default to zero or guess broker values.

Explicitly undecided product facts (do not infer defaults):
- Local model/runtime winner: Ollama vs llama.cpp on laptop and desktop (benchmark pending).
- Numeric ATR risk curve floors/ceilings/max, per-trade hard caps, weaker-tier caps, tier trade counts/elapsed periods, deterioration thresholds, correlation estimator/window/groups and reserve formula.
- Metric annualization/risk-free convention and numerical stable-region definition.
- Missing cost assumptions when broker data omits costs; disclosure and blocking behavior per case.
- Cloud backup provider, key management and bandwidth/capacity.
- News-source list and implementation phase (later phase; free permitted sources only).
- Job intervals and resource thresholds (configurable, not hard-coded without a decision).
- Precise order-block / fair-value-gap definitions if included (deferred until precise rule acceptance).

## Brand Commitments

Product name: Superbot. No other binding brand, voice, naming, personality or accessibility commitments recorded.

## Evidence on Hand

Specification pack at C:\SuperBot root: PRD.md (product requirements), schema.md (domain contracts), rules.md (engineering rules and ECC build loop), architecture.md (component boundaries), task.md (prioritized build ledger with milestone status), context.md (current reality, decision register and evidence), design.md (quant-terminal UI design brief), AGENTS.md (agent authority model), START_PROMPT.md, README.md, MANIFEST.json. Implementation under src/superbot/ (contracts, data, engine, simulation, strategy, risk, execution, m9/m10/m11 services, observability, persistence, supervisor), tests/ (unit, integration, e2e), docs/adr/ (ADR-001 package layout, ADR-002 OHLCV storage, ADR-004 UI/API/chart stack, ADR-006 engine selection). Baseline synthetic POC results in superbot_poc_kit/results/. Real XM MT5 terminal verified for read-only symbol/spec/account discovery. Hundreds of unit/integration tests pass; pytest + ruff clean.

## Product Principles

1. AI proposes; deterministic code verifies; risk limits decide — no agent may override risk or write official state.
2. Local-first, local AI only; no hosted inference; no live trading path in V1.
3. Everything versioned and evidenced: schemas, configs, strategies, experiments, audit events; corrections append, never silently edit or delete.
4. Missing or unverifiable inputs block the operation; never guess broker values or default costs to zero.
5. Reproducibility first: fixed fixtures, pinned versions, deterministic replays, stable signal IDs and dedup.

## Accessibility & Inclusion

Keyboard navigation, focus visibility, contrast, semantic labels and meaningful empty/loading/error states are required on dashboard surfaces (per design.md §5). No product-specific accessibility user need or conformance level (e.g., WCAG) was established; none is invented here.
