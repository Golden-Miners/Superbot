# Superbot Application Agents and Authority Model

## 1. Governance rule

**AI proposes; deterministic code verifies; risk limits decide.** Agents are advisory/research specialists. They cannot place live trades, alter official state directly, approve their own candidate, override risk checks or rewrite audit history. The deterministic orchestrator and domain services own lifecycle transitions.

The user previously considered ten strategy agents. The later locked decision is a **shared framework with separately versioned strategy implementations/configurations**, not one separate LLM agent per strategy. Parallel agents are allowed only where measured CPU/RAM and task independence justify them. One shared local model with sequential tasks is acceptable on resource-constrained machines.

## 2. Components / roles

### Deterministic workflow orchestrator
Owns workflow state, dependency graph, job priority, timeouts, retries, idempotency, checkpointing, cancellation and state transitions. Validates inputs/outputs against versioned contracts and determines which dependent tasks can proceed when another agent fails. It does not use LLM prose to establish authority.

### Data-quality and source agent (read-only, advisory)
Can explain anomalies and suggest repair/reacquisition paths. Deterministic validators detect and record gaps, duplicates, suspicious bars, staleness, timestamp errors and provider disagreement. Agent claims never clear a failed data-quality gate.

### Market analyst agent
Summarizes trend/regime, volatility, momentum, liquidity/market-structure evidence and relevant technical conditions using supplied read-only, point-in-time data. It cites bar ranges, timestamps and feature identifiers. It cannot issue unvalidated executable orders or set risk limits.

### Strategy-family proposer(s)
Propose machine-testable rules, parameters and falsifiable hypotheses for: (1) trend-following/pullback; (2) liquidity sweep/market structure; (3) quantitative/statistical. Every proposal must define inputs, entry, exit, invalidation, expiry, max holding period or explicit none, reverse-signal policy, and trailing/partial-exit conditions if used. Concepts such as order blocks/FVG must be precisely specified before implementation.

### Research reviewer / adversarial reviewer
Challenges evidence, leakage risk, baseline comparisons, trade count, overfit indicators, costs, parameter sensitivity and failure modes. Returns structured findings with references; cannot promote a candidate. Unresolved high-impact conflict blocks downstream decisions.

### Strategy rule/schema validator (deterministic)
Validates schema, allowed features, parameter bounds, references, temporal causality, required exits/invalidation and versioning. Rejects invalid or incomplete proposals before simulator execution.

### Backtest and simulation service (deterministic, not an LLM agent)
Runs the authoritative event-driven simulation with verified specs/cost models, conservative OHLCV event ordering and reproducible state. Fast sweeps can be used for exploration but cannot replace primary simulation/final validation.

### Validation gate service (deterministic)
Runs chronological splits, OOS and walk-forward metrics, trial accounting, leakage tests, neighboring-parameter robustness, baseline comparisons, costs and stress tests. Emits PASS/FAIL/BLOCKED with machine-readable reasons and exact config/version refs.

### Portfolio and risk service (deterministic)
Enforces portfolio-wide, strategy-level and correlation-group caps, daily loss and drawdown rules, ATR-relative volatility controls, tier allocation, position-sizing inputs and signal competition. Missing/unverifiable inputs block entries. This service cannot depend on model availability.

### Portfolio/strategy decision coordinator (“CEO” concept)
May synthesize analyst, strategy, news/sentiment and validation evidence into a structured research recommendation: proceed, defer, reject or request evidence. It has no privileged execution authority. Deterministic lifecycle/risk gates override it. “No trade/no candidate” is a valid output.

### Diagnostics and failure classifier
Classifies failures into data, strategy, execution-model, risk, runtime, UI/operation or infrastructure categories. Distinguishes execution-model errors from strategy failure. May propose one bounded, testable change with evidence, expected effect, risk and rollback plan. Cannot edit the known-good version directly.

### News and sentiment agents (later phase)
Use free permitted sources only. Produce source-attributed records with publication time, instrument, category, sentiment, confidence and supporting text. News/sentiment is research context/filter only. Stale/missing news blocks news-dependent decisions while independent technical work may proceed. News cannot override entries or risk gates.

### Research librarian / evidence recorder
Persists dataset/code/strategy/parameter/config hashes, trials, results, failures, citations/URLs and accepted lessons. Saves only verified, evidence-linked knowledge as approved project knowledge; unverified claims remain proposals.

## 3. Agent interface contract

All messages use versioned schemas in `schema.md`. Every output includes:
- `schema_version`, `message_id`, `run_id`, `agent_id`, `role`, `created_at_utc`.
- `status`: `complete`, `incomplete`, `rejected`, `blocked`, or `error`.
- `inputs_ref` or immutable identifiers for relevant data/features/config.
- `claims`/`findings` with evidence references and confidence only when confidence has a defined interpretation.
- `limitations`, `missing_evidence`, `warnings` and proposed next action.
- Strategy proposals: explicit rules, parameter constraints, hypothesis, invalidation and expected failure modes.

No plain-text-only response may advance lifecycle state. Unknown fields are rejected or quarantined according to a versioned compatibility policy; malformed values are not silently coerced.

## 4. Permissions

- Agents read scoped, immutable market data and approved experiment artifacts.
- Research agents create proposals in a staging area only.
- Only deterministic services write official strategy versions, risk configuration, job state, validation results, simulation ledger and audit events.
- Agent tools have no access to broker order submission. No live execution service is added in this scope.
- No direct database mutation by an LLM. Writes flow through validated service APIs.
- Read/write permissions are role-scoped and least-privilege. Broad research access is not authority to set risk or lifecycle state.

## 5. Failure behavior

- One agent failure does not cancel independent safe work; missing evidence is marked.
- Dependent steps are blocked when required evidence is absent.
- Retries are bounded and recorded. Use a qualified fallback only if task-specific tests establish suitability; otherwise skip the AI-dependent task and mark incomplete.
- High-impact tasks may be repeated within a configured budget. Unresolved conflict blocks the decision and is retained in audit.
- Model/runtime/quantization/config changes are new candidates requiring qualification for correctness, schema validity, repeatability, latency and memory.
- No agent may “heal” a failed risk/data/audit gate by editing the result.

## 6. Agent build and validation requirements

For each agent, define role/scope, versioned input/output schema, permission tests, malformed output tests, timeout/retry tests, failure behavior, evidence tests and prompt-injection tests for untrusted market/news/repository text. Test deterministically using fixed fixtures before model-backed use. Document model/runtime qualification by task; exact model selection remains OPEN.

## 7. Runtime agents versus coding agents

OpenCode/ECC coding workflows are separate from Superbot runtime agents. ECC agents/skills/loops help build, test and review the codebase; do not copy them into the trading-runtime graph unless a concrete tested requirement justifies it. `AGENTS.md`, `rules.md` and `task.md` remain authoritative project instructions/build ledger.
