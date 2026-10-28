# Superbot Dashboard and UX Design Brief

## 1. Direction

Modern **quant-terminal** interface: graphite/dark canvas, cyan/teal accents, restrained highlights, clear hierarchy and high but readable information density. This is a research, validation, risk and simulation workstation—not a retail ticket and not a live-execution terminal.

Do not build only a static mockup. Use real API contracts/states, representative fixtures clearly marked synthetic, browser tests, screenshots from actual runs and keyboard/responsive checks. Do not claim visual verification without an actual browser run or supplied evidence.

## 2. Primary surfaces

### Overview
- Health row: API, PostgreSQL, worker supervisor, model runtime, MT5 read-only status, last update, data freshness and backup state.
- Instrument/timeframe coverage for Gold, Silver, Bitcoin, Ethereum and US Oil × M5/M15/H1/H4. Show unavailable/unverified mappings; never fabricate values.
- Queue and active research/validation jobs.
- Strategy lifecycle: proposed, blocked, validating, shadow, internal simulation, archived.
- Simulated equity, open risk, daily-loss usage and drawdown with limit context.
- Highest-priority alerts and explicit unresolved blockers.

### Market/data explorer
- OHLCV chart with provider/source, symbol mapping, timeframe, timestamp convention, freshness and coverage.
- Price/volume and optional deterministic overlays labelled by definition/version.
- Data-quality state for gaps, duplicates, suspicious values, stale feed, source disagreement or unverified specs.
- Never silently merge providers. Distinguish synthetic fixture, imported history and broker feed.

### Research queue
- Job status, dataset/symbol/timeframe, strategy/config version, priority, resource use, progress/checkpoint, start/duration and pause/resume/cancel.
- Prevent duplicate overlaps; show why blocked/deferred.
- Confirm potentially destructive cancellation when uncheckpointed work could be lost.

### Strategy/signal workbench
- Strategy family/version/parameters and machine-readable entry/exit/invalidation rules.
- Proposal source (deterministic baseline vs AI), evidence refs and schema validation outcome.
- Signal expiry/invalidation, data freshness, risk gate and stable signal ID.
- Rejected signal shows deterministic rejection reason. Never present an AI suggestion as approved trade.

### Validation/experiment details
- Chronological split, 3+ walk-forward windows, OOS metrics/trade count, costs and missing-cost warnings.
- Parameter-neighbor robustness, baseline comparisons, trial count, untouched-test status and leakage result.
- Each gate explicitly shows `PASS`, `FAIL`, `BLOCKED` or `NOT RUN`, with timestamp/config/evidence.
- Promotion action only when backend confirms deterministic eligibility and role permissions. Human stage approvals remain explicit.

### Portfolio/risk/internal simulation
- Simulated positions, entry/exit, stop/partial event timeline, mark-to-market inputs, costs, exposure and P&L.
- Portfolio, strategy and correlation-group risk against configured limits.
- Daily baseline, drawdown peak, halt state and human-approved resume record.
- Missing/stale specs or unverifiable sizing must show blocked, never zero-risk/green.
- Label all values internal-simulation/research; no live orders in V1.

### Audit/experiment library
- Search run ID, strategy/version, symbol/timeframe, date, data hash, outcome, gate, failure class and commit.
- Inspect append-only events, evidence refs, correction linkage and version refs; exportable reports.
- Failed experiments remain searchable; no silent deletion.

### Settings/profiles
- `research`, `internal-simulation`, future guarded `demo-readiness` with clear stage boundaries.
- Only authorized owner may change sensitive settings. Show value, validated range/source, version, actor/reason, timestamp and last-known-good.
- Invalid values rejected and prior good config retained. Secrets redacted and non-exportable.
- No control to enable live orders in this scope.

## 3. Visual states and interaction

- **Healthy/eligible:** supported by verified status.
- **Warning/degraded:** stale data, optional source missing, resource pressure, backup overdue or partial capability.
- **Blocked/failure:** mandatory gate failed, invalid metadata, audit corruption, risk limit breach, test not run or required input missing.
- **Pending/in progress:** show state/next step; do not imply success.

Color must not be the only signal; include text/icon/accessible label. Avoid broad colored summary cards and excessive badges. Use readable dense tables, precise units/number formatting and timezone labels. Never imply simulated/model-generated values are live broker data.

## 4. Alerts

Routine completion goes to notification center. Persistent warnings remain until acknowledged/resolved. High-priority alerts include risk breach; data/audit failure; stale/unverified broker specs; crash/recovery required; backup/restore failure; runtime outage affecting critical work; suspected unauthorized config change. Each alert links to an auditable event and actionable diagnostics.

## 5. Responsive/performance requirements

- Desktop/laptop first; do not assume multiple monitors or high resolution.
- Paginate/filter/virtualize large tables only where evidence warrants it.
- Do not put full history or huge experiment artifacts in UI memory; use query APIs/server-side pagination.
- UI rendering/animation must not starve critical simulation/risk workers under load.
- Keyboard navigation, focus visibility, contrast, semantic labels and meaningful empty/loading/error states required.

## 6. OPEN tooling choices

Inspect repo and environment first. In a fresh repository, compare feasible local UI approaches and record an ADR before selecting a framework. Evaluate `tradingview/lightweight-charts` only after checking current API/version/license/attribution. Use Stitch only if actually available and useful for exploration; mockups are not implementation proof. Use Playwright only if its installed tool and target app are available; retain real run/screenshot evidence.

## 7. UI acceptance checklist

- Critical states sourced from real backend, not mocked success.
- Synthetic fixture data clearly labeled.
- Source, timestamps/timezone and freshness visible.
- Gate states distinguish PASS/FAIL/BLOCKED/NOT RUN.
- Rejected signal/job includes reason and evidence.
- Backend enforces authorization; hiding a button is insufficient.
- No public network binding; remote access only through approved private VPN.
- Error/loading/empty states, keyboard use and laptop/small-screen layout tested.
- Browser evidence records revision and viewport where available.
