# Superbot Canonical Schemas and Data Contracts

**Purpose:** Define contracts before implementation. These are required logical contracts; exact Python class and physical database names can be selected in an ADR. Every persisted contract has a schema version and migration policy.

## 1. Global conventions

- Every durable/inter-agent contract has `schema_version`.
- Persisted timestamps are UTC ISO 8601/timezone-aware; preserve source timestamp and timezone metadata where relevant.
- Money/risk accounting uses Decimal/fixed-point or integer ticks/lots as appropriate. Do not use binary-float rounding as final authority for risk/ledger decisions.
- Enums and state transitions are explicit; reject invalid values/transitions.
- Jobs, experiments, decisions and audit events have stable IDs/correlation IDs.
- Large outputs live in versioned files addressed by immutable hash/reference, not oversized event rows.
- AI-produced fields remain proposals/unverified until deterministic validation accepts them.
- Market/news/repository text is untrusted data, never tool instructions.

## 2. Instrument specification

```yaml
schema_version: string
instrument_id: string
provider_id: string
provider_symbol: string              # discovered exact symbol, never guessed
asset_class: enum                   # metal, crypto, energy; extend only by decision
quote_currency: string | null
base_currency: string | null
contract_size: decimal | null
tick_size: decimal | null
tick_value: decimal | null
volume_min: decimal | null
volume_max: decimal | null
volume_step: decimal | null
price_precision: integer | null
volume_precision: integer | null
trade_sessions_ref: string | null
server_timezone: string | null
source_updated_at_utc: timestamp | null
verified_at_utc: timestamp | null
verification_status: enum           # verified, stale, ambiguous, unavailable, rejected
source_metadata_ref: string
```

Null does not mean zero. Missing/stale fields needed for a simulation or sizing block that operation. Never substitute typical broker values.

## 3. OHLCV bar

```yaml
schema_version: string
provider_id: string
instrument_id: string
provider_symbol: string
mapping_version: string
timeframe: enum                      # M5, M15, H1, H4; extend only by decision
bar_open_utc: timestamp
bar_close_utc: timestamp | null
source_timestamp: string | null
source_timezone: string | null
open: decimal
high: decimal
low: decimal
close: decimal
volume: decimal | null
volume_kind: enum | null            # tick, real, unknown as source permits
source_revision: string | null
quality_status: enum                # valid, gap_adjacent, suspicious, invalid, stale
available_at_utc: timestamp
source_record_ref: string
```

Validate numeric finiteness, OHLC relationships, time ordering, uniqueness, interval alignment and availability. Do not automatically synthesize missing bars. Keep source bars immutable; repaired/cleaned data is a separate derived version with provenance.

## 4. Dataset manifest

Required logical fields: `schema_version`, `dataset_id`, `content_hash`, source ID(s), instrument/timeframe coverage, start/end UTC, row/bar count, bar schema version, creation/update timestamps, acquisition/cleaning code version, quality report reference, parent dataset refs, excluded period/record refs, coverage by instrument/timeframe, storage URI and limitations. Dataset ID/hash must uniquely identify experiment data.

## 5. Strategy definition/version

```yaml
schema_version: string
strategy_id: string                 # stable logical identity
strategy_version_id: string         # immutable version identity
family: enum                        # trend_pullback, liquidity_structure, quantitative_statistical, extension
status: enum
rule_spec_ref: string
parameter_schema_ref: string
parameter_values_ref: string
hypothesis: string
inputs: [feature_ref]
entry_rules: structured_rule[]
exit_rules: structured_rule[]
invalidation_rules: structured_rule[]
expiry_policy: structured_policy
max_holding_policy: structured_policy # explicit none or measured bound
reverse_signal_policy: enum          # versioned policy
stop_policy: structured_policy
partial_exit_policy: structured_policy | null
allowed_instruments: [instrument_id]
allowed_timeframes: [timeframe]
created_at_utc: timestamp
created_by: string
parent_version_id: string | null
code_commit: string
rule_schema_version: string
```

Executable strategies cannot rely on vague prose. If BOS/CHOCH/OB/FVG are used, formalize and test them. Parameter units/bounds are mandatory. Material rule/parameter/risk-rule changes create a new version and restart the required lifecycle.

## 6. Signal proposal/record

Fields: `schema_version`, stable `signal_id`, `strategy_id`, `strategy_version_id`, `instrument_id`, `timeframe`, `direction`, `signal_created_at_utc`, `feature_cutoff_utc`, `entry_eligibility_time_utc`, source bar refs, feature refs, proposed entry type/constraints, stop/invalidation, target/exit policy, expiry timestamp or policy ref, invalidation timestamp if applicable, `proposal_source` (deterministic/AI), `validation_status`, `risk_check_ref`, `decision_status`, deterministic `decision_reason_codes`, data-freshness ref and audit refs. Enforce feature cutoff/signal/entry temporal causality as required by strategy. Exceptions must be explicit policy, not a bypass.

Deduplication uses strategy, instrument, direction and stable identity. Re-entry/reversal follows versioned rules.

## 7. Risk check result

```yaml
schema_version: string
risk_check_id: string
checked_at_utc: timestamp
portfolio_state_ref: string
signal_ref: string
instrument_spec_ref: string
strategy_version_ref: string
requested_cash_risk: decimal | null
stop_distance: decimal | null
proposed_quantity: decimal | null
open_portfolio_risk_pct: decimal | null
daily_loss_pct: decimal | null
portfolio_drawdown_pct: decimal | null
strategy_risk_pct: decimal | null
correlation_group: string | null
correlation_group_risk_pct: decimal | null
volatility_measure_ref: string | null
passed: boolean
reason_codes: [enum]
required_input_status: object
config_version: string
```

Failed/blocked check has zero approved quantity and explicit reason. Missing required input cannot mean zero exposure or pass. No AI override field exists.

## 8. Simulated order/fill/position events

Use an event-based ledger, not only an overwritten current-position row.

Logical fields: `schema_version`, `event_id`, `run_id`, `position_id`, `order_id`, `signal_ref`, `strategy_version_ref`, `instrument_id`, `event_type` (created, accepted, rejected, triggered, filled, partial_fill, stop_changed, partial_exit, close, cost_applied, reconciliation, etc.), `event_time_utc`, source bar ref, quantity, price, gross P&L, commission, spread cost, slippage cost, swap/funding cost, other cost, net P&L, stop/target after event, reason code, simulator policy version, instrument spec ref, prior/new state hashes and audit ref.

Amounts can be null when inapplicable, but event-type validation decides what is required. Corrections append linked correction/reconciliation events; never mutate originals. Fixed inputs/config/seeds must yield causally consistent, deterministic event order.

## 9. Validation and experiment record

Required fields:
- `schema_version`, `experiment_id`, `run_id`, `trial_id`, strategy/version, code commit, environment/dependency lock, dataset ID/hash and lineage.
- Exact parameters, seeds, splits, walk-forward windows, feature/cost/model config versions.
- Start/end times, status (`running`, `passed`, `failed`, `blocked`, `incomplete`, `cancelled`) and failure class/reason.
- Trades, returns, costs, drawdown, PF, Sharpe, Sortino and metric conventions/annualization/risk-free assumptions.
- Per-window OOS results; parameter-neighbor matrix/summary; no-trade/simple/previous-approved baselines; cost stress; leakage results; data-quality report; trial count and multiple-testing controls.
- Gate IDs/results/config versions/evidence references.
- Resource metrics if available: wall time, CPU time, peak process-tree memory, I/O, throughput, startup and failure rate.
- Limitations, unavailable costs and irreproducibility flags.

Summary metrics alone cannot substantiate `passed`; every gate needs stored result/config/evidence.

## 10. AI agent message/proposal

Required fields: `schema_version`, `message_id`, `run_id`, `agent_id`, `role`, `model_id/version`, `runtime/version`, `created_at_utc`, `status`, input refs, claims/findings with evidence refs, missing evidence, warnings, limitations, optional proposal ref and validation status. Raw model output, if retained, requires provenance and redaction. Parse/validate before it can enter an official workflow.

## 11. Job/resource record

Fields: `job_id`, `job_type`, `created_by`, priority tier, requested interval, dedupe key, status, input refs, config version, dependencies, created/started/updated/finished UTC, checkpoint ref, attempt count, failure class/reason, resource limits/measurements, cancellation request/outcome and audit refs. On restart reconcile interrupted state before new jobs.

## 12. Configuration version

Non-secret config: `config_id`, version, profile, schema version, validated values, actor, reason, creation timestamp and previous/last-known-good ref. Secret references are local protected-storage IDs only; never persist secret values here. Invalid configuration is rejected; retain last-known-good.

Profiles: `research`, `internal-simulation`, and future guarded `demo-readiness`. Do not add a live-trading profile/order flag in this scope.

## 13. Audit event

Required: `schema_version`, audit event ID, event time UTC, actor type/ID, action, object type/ID, prior/new version refs, reason, input evidence refs, outcome, correlation ID, integrity mechanism/previous-event hash if selected, and `correction_of` when correcting a prior event. The exact hash-chain implementation can be selected by ADR, but audit must be append-only and integrity-checkable.

## 14. News event (later phase)

Schema version, news ID, source/URL, publication/retrieval UTC, affected instrument(s), event category, sentiment label and defined confidence semantics, supporting text/snippet/hash, language, staleness status and attribution. Free permitted sources only. Missing/stale news blocks news-dependent decisions only.

## 15. Backup manifest

Schema version, backup ID/time, local/cloud destination refs, encryption/key identifier (never key material), component manifests, DB checksum, dataset hashes, artifact refs, excluded-secret classes, integrity result, retention expiry, restore-test ref and errors. Credentials remain outside backup and manifest.

## 16. Schema lifecycle

- Every change includes versioned migration and compatibility tests.
- Immutable experiment/audit records retain creation schema version.
- Migration never silently changes historical result meaning; preserve original plus derived interpretation.
- Unknown critical fields or invalid enum/state are rejected/quarantined, never silently cast to success.
