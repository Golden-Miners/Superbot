# Superbot Debugging, Incidents and Failure Learning

## 1. Objective

Find and verify root cause, preserve evidence, make the smallest correction, add a regression test and update project records. Never hide or overwrite failed results. Use the ECC loop in `rules.md`.

## 2. Required failure record

For every implementation/validation failure, record:
- Incident/issue ID and UTC date/time.
- Task/milestone, branch and commit.
- Relevant environment: OS, Python/runtime/dependency versions, CPU/RAM/disk state.
- Exact command/action and exit code.
- Redacted log excerpt and local log path where retained.
- Expected vs actual result.
- Reproduction steps; deterministic or intermittent.
- Classification: application, domain rule, data/fixture, temporal leakage, engine integration, dependency/environment, resource/performance, persistence/recovery, security/permissions, UI, specification ambiguity.
- Root-cause status (confirmed/likely/unknown) and evidence.
- One corrective hypothesis and why evidence supports it.
- Regression test added/updated and exact result.
- Fix commit/version, residual risk and rollback path.
- Documents updated.

Redact secrets and private account info before writing Markdown.

## 3. Investigation sequence

1. Stop uncontrolled retries and preserve first failure output.
2. Confirm Git status and reproduce with same environment/config.
3. Verify the test reached the intended code path. Launcher exit code alone does not prove child-process resource measurement.
4. Correlate logs and state transitions using run/task IDs, data/schema/config versions and exact timestamps.
5. Check input quality, source freshness, candle/timezone alignment, provider/symbol metadata and config before assuming a strategy bug.
6. Isolate using the smallest deterministic fixture. For engine mismatch, compare event-by-event fills and state to custom baseline.
7. Form one root-cause hypothesis and gather evidence/test that distinguishes it from alternatives.
8. Make one minimal fix; rerun failed test, relevant regressions, quality/security checks and recovery tests where relevant.
9. Use ECC quality/review if installed; otherwise record equivalent manual review.
10. Update `task.md`, `context.md` if state changed, and this file. Update `schema.md`/`architecture.md` when a contract/design issue was found.

## 4. Domain diagnostics

### Data vs strategy failure
- Check bar source/hash, gaps/duplicates, source identity, mapping, timezone/candle boundaries and freshness first.
- Verify feature availability timestamps and leakage tests.
- Do not label corrupted/stale data as strategy underperformance.

### Fill/simulator mismatch
- Compare bar/event timeline, order trigger, next-open convention, spread/slippage, stop-gap rule, stop-first ambiguity, lot/tick/contract specs, cost order and partial/stop-adjustment events.
- Verify engine-specific implicit behavior; disable/replace it if inconsistent with Superbot's explicit policy.
- Save minimal reproducible fixture and expected event trace.

### Risk breach or incorrect sizing
- Treat as high severity. Halt new entries in affected scope; preserve simulated state.
- Inspect verified specs, stop distance, cash-risk budget, conversion inputs, lot step/minimum, portfolio/strategy/group exposure, daily baseline, drawdown peak and rounding.
- Do not “fix” by relaxing accepted limits without user approval.
- Add boundary-equality, missing/stale-input and concurrent-signal tests.

### Leakage suspicion
- Fail candidate until reviewed. Inspect feature availability, indexing/window alignment, split boundaries, normalization fit, target/label access and future candle references.
- Preserve run/trial metadata; corrected strategy version restarts validation.

### AI/model failure
- Record model/runtime/version/quantization, input refs, schema version, output errors, latency, memory and retry/fallback outcome.
- Retry only within configured limits. Qualified fallback if verified; otherwise mark dependent task incomplete.
- Malformed/conflicting output cannot advance lifecycle.

### UI/API failure
- Reproduce via local API and browser test if available. Check authorization/session and server logs using correlation ID.
- Capture screenshot only if browser run actually occurred; record URL/state/viewport/test setup.
- UI availability cannot bypass backend authorization or domain gates.

### Resource/startup/recovery failure
- Monitor full process tree, not only `py.exe`; record parent/child PIDs, RSS/working set, actual CPU time (do not sum cumulative CPU readings repeatedly), disk I/O, pagefile pressure, duration and workload size.
- Distinguish sampling gaps from low memory use; short processes can finish between samples.
- Reproduce crash/restart with known simulated-position/pending-signal state and confirm reconciliation before resume.

## 5. ECC loop and stop conditions

Use `rules.md` loop G. Do not repeat the same patch without new evidence. Verify whether ECC commands exist before calling them; if a loop is active, inspect status before starting another. A coding loop ends on verified acceptance, a documented blocker or an explicit safety stop—never an infinite loop.

PRD's three failed validation attempts apply to a strategy version, not to software-debug retry count.

## 6. Known baseline measurement cautions

See `context.md` and `memory.md`:
- Synthetic correctness passed, but no real market data/engine/MT5 integration was tested.
- `tracemalloc` is not process RSS.
- 9 MB observation likely measured the launcher, not workload.
- Second monitor observed 25.77 MB Python child working set for five samples; cumulative sampled CPU values were wrongly summed and are not valid CPU time.
- New benchmark must capture process tree robustly with a sufficiently long representative workload.

## 7. Severity

- **Critical:** risk bypass, potential order execution, secret exposure, audit mutation/loss, confirmed leakage in a promoted candidate, corrupted official ledger.
- **High:** wrong money/fill accounting, loss of data lineage, recovery failure, unauthorized settings changes, promotion despite failed mandatory gate.
- **Medium:** reproducibility/workflow failure without unsafe transition; wrong dashboard state while backend remains protected.
- **Low:** non-critical visual/usability issue or non-blocking documentation issue.

Critical/high defects block release and promotion. Never downgrade severity only to unblock a milestone.
