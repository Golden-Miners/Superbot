# Superbot Durable Memory and Session Handoff

This file stores concise durable facts. It does not replace the complete requirements in `PRD.md`, `architecture.md`, `schema.md` or the task ledger in `task.md`.

## 1. Source-of-truth hierarchy

1. Latest explicit user-confirmed decision.
2. Measured reproducible local evidence or verified official source/commit.
3. Approved architecture decisions (ADRs).
4. Current requirements/docs.
5. Prior-session summary or learned instinct.
6. Model inference, which remains a proposal until verified.

If records conflict, identify the conflict and update source-of-truth docs. Memory must not quietly override the user.

## 2. Permanent project facts

- Project: Superbot, new standalone app; do not derive it from GoldMasters.
- Initial mode: research, historical backtesting, signal generation and internal simulation only. No live trading/order code in scope.
- Local-first, Python-first, Windows-native, ₹0 hosted inference budget, English-only.
- First test machine: Windows 10 Lenovo laptop, approximately 8 GB RAM, 2 logical CPU threads and HDD. Later target: Windows 10 desktop, approximately 12 GB RAM, Intel i5-3470 and AMD Radeon R9 290. Exact GPU VRAM/driver, free disk and disk health remain unverified.
- Assets: Gold, Silver, Bitcoin, Ethereum, US Oil. Timeframes M5, M15, H1, H4.
- Initial provider: XM MT5, read-only market data/account balance/specs. Verify actual symbols/metadata in user's terminal.
- Local PostgreSQL is selected for application records. OHLCV storage format remains OPEN; benchmark Parquet and alternatives.
- Governing principle: AI proposes, deterministic code verifies, risk limits decide.
- Three reference strategy families: trend-following/pullback; liquidity sweep/market structure; quantitative/statistical. Shared framework, separately versioned strategies, not one LLM agent per strategy.
- Risk limits: open risk 5%; daily loss 3% of starting daily equity; portfolio DD halt 10%; strategy OOS DD <=15%; normal OOS minimum 100 completed trades; >=3 walk-forward windows; PF >=1.20; Sharpe >=1.0; Sortino >=1.5; >=2 of 3 windows positive. Preserve exact metric convention/config.
- Four evidence tiers use multipliers 0.25x/0.50x/0.75x/1.00x; monthly reviews; maximum 10% relative risk increase per review. Exact tier, volatility and correlation thresholds remain OPEN.
- After three failed validation attempts, disable/archive that strategy version and preserve records. Material changes create a new version and restart its lifecycle.
- Backups: daily local plus encrypted cloud, 30-day retention, integrity verification and monthly restore test. Cloud destination/key management OPEN. No secrets in backup/sync.
- User confirmed on 2026-10-28 that license review for previously considered repos is clear for their purposes. Record exact license/version for adopted dependencies; do not reopen already reviewed components without changed facts/new component.

## 3. Local POC facts (user measured on Windows laptop)

- `py --version` → Python 3.14.7.
- Baseline command: `py superbot_poc.py --warmups 1 --repetitions 5`.
- Report timestamp: `2026-10-28T12:30:05.417727+00:00`.
- Correctness `PASS`; seven synthetic checks: OHLCV validity/chronology; next-bar-open entry; stop-first on ambiguous same-bar SL/TP; explicit spread/commission; adverse stop-gap fill; deterministic portfolio/daily-loss/drawdown gates; signal timestamp before entry.
- Fixture: 10 bars; SHA-256 `e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd`.
- Benchmark: 2,000 iterations/run, one warmup, five timed runs: 54.8336, 25.7248, 30.3061, 28.4241, 29.7840 ms; median 29.7840 ms; range 29.1088 ms; median `tracemalloc` peak 160 bytes. Tiny synthetic fixture; not market-performance evidence and not process RSS.
- Computer physical RAM: `7,983,263,744` bytes (~7.44 GiB); `TotalVisibleMemorySize` 7,796,156 KiB; `FreePhysicalMemory` 2,109,516 KiB (~2.01 GiB) at that instant. Free memory is only a snapshot.
- `Get-Command py` → `C:\WINDOWS\py.exe`.
- First resource monitor: 9 MB/10 samples/CPU 0.08, likely sampled only launcher; do not use as workload metric.
- Second monitor: exit code 0, sampled Python child working set peak 25.77 MB with 5 samples. CPU readings were cumulative values summed repeatedly and are invalid as total CPU time. Sampling was too short to establish whole-app resource needs.
- Neither monitor is a robust full process-tree benchmark. No candidate engine, PostgreSQL, MT5 link, local model runtime or complete app has been tested on the laptop from this evidence.

## 4. Canonical contracts implemented

- `src/superbot/contracts/instrument.py` (M1.2): `InstrumentSpec`, `AssetClass`, `VerificationStatus`, `InvalidInstrumentError` — schema.md §2; Decimal-or-null numerics, required-field validation, null never means zero.
- `src/superbot/contracts/ohlcv.py` (M1.2): `OHLCVBar`, `Timeframe` (M5/M15/H1/H4), `VolumeKind`, `QualityStatus`, `InvalidOHLCVError` — schema.md §3; OHLC relationships, time ordering, M5/M15/H1/H4 interval alignment, availability required.
- `src/superbot/contracts/provider.py` (M2.1): `ProviderSpec`, `ProviderType`, `ProviderVerificationStatus`, `InvalidProviderError` — provider/source identity and provenance; unknown/null metadata preserved, no guessed broker values.
- `src/superbot/data/quality.py` (M2.2): `validate_chronology`, `validate_no_duplicates`, `validate_gaps`, `validate_freshness`, `validate_prices`, `validate_availability` + `GapReport`/`FreshnessReport`/`PriceReport` — collection-level data-quality checks on OHLCV bar collections.
- `src/superbot/data/session.py` (M2.4): `SessionValidator`, `SessionTimezoneState`, `UnknownTimezoneError`, `SessionBoundaryError`, `validate_session_boundaries` — session/timezone boundary validation; unknown timezone/session blocks work, never assumed; UTC canonical preserved separately.
- `src/superbot/data/mt5_adapter.py` (M2.5): `Mt5Adapter`, `Mt5AdapterError`, `Mt5SymbolNotFound` — read-only MT5 symbol/spec discovery; lazy MetaTrader5 import; no order methods; `initialize(path)` launches/connects to real terminal; null-preserving spec mapping; inferred asset class flagged AMBIGUOUS. Verified against BOTH a fake MetaTrader5 module AND the real XM MT5 terminal on this laptop (C:\Program Files\MetaTrader 5\terminal64.exe): terminal initializes, symbols discovered, specs returned, account info returned, shutdown clears state.
- metatrader5 import resolution: package imports correctly as `MetaTrader5` (capital M, the documented import name), v5.0.6231, with `symbol_info` and `copy_rates_from_pos`. Earlier `ModuleNotFoundError` was from using lowercase `metatrader5`.
- `src/superbot/data/storage_benchmark.py` (M2.6): `StorageBenchmark`, `StorageBackend`, `BenchmarkResult`, `UnknownFormatError` — storage format benchmark contract.
- `src/superbot/data/storage_backends.py` (M2.6): `ParquetBackend`, `SQLiteBackend`, `CSVBackend` — concrete OHLCV storage backends.
- ADR-002 (`docs/adr/0002-ohlcv-storage-format.md`): Parquet (zstd) selected as primary OHLCV market-history store; CSV for interchange only; SQLite rejected as primary (largest footprint). Benchmark results: 5000 bars — Parquet write=2154ms/read=89ms/14KB; SQLite write=344ms/read=38ms/82KB; CSV write=36ms/read=109ms/45KB.

## 5. Memory hygiene / decision changes

When a user confirms/rejects/changes a choice, update the source-of-truth document and `context.md`; mark prior decisions superseded rather than deleting history; record date/impact/ADR/task. Do not store secrets, passwords, API keys, broker account identifiers or sensitive account data in this file or external memory.

## 6. Session handoff template

At safe context boundaries, update:
- Current milestone/task:
- Current branch/commit:
- Completed since last handoff (with evidence):
- Exact commands/tests/outcomes:
- Files changed:
- Open blockers/decisions:
- Known defects/limitations:
- Next smallest task:
- Exact next command/action:

Do not compact context mid-edit or mid-debug. Persist this handoff first.
