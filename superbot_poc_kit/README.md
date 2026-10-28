# Superbot isolated POC control baseline

**Purpose:** establish a small, deterministic reference test for Superbot's simulator POC and collect machine-specific measurements on the target Windows computer.

**Safety:** this package uses only synthetic OHLCV fixtures and Python's standard library. It makes no network or broker connections, reads no credentials, and writes reports only into this package's `results` folder. It is not a trading strategy, a production simulator, or a profitability test.

## Run on the Windows Lenovo laptop

1. Extract this folder to a new, isolated directory.
2. Open PowerShell in that directory.
3. Check Python: `py --version` (Python 3.11+ recommended for the broader project; this script itself uses standard-library features available in recent Python 3 versions).
4. Run correctness tests and five-repeat baseline benchmark:

   `py superbot_poc.py --warmups 1 --repetitions 5`

5. The JSON report is printed and saved under `results/`.
6. Repeat on the desktop later using the same script and Python version where possible.

No packages need to be installed for this baseline.

## What this baseline checks

- OHLCV integrity and increasing timestamps
- Signal-to-entry chronology and next-bar-open entry
- Conservative stop-first treatment when stop and target are both touched
- Worse opening-price fill when a stop is gapped through
- Explicit spread and commission arithmetic
- Basic deterministic portfolio, daily-loss, and drawdown gates
- Warm-up plus at least five measured repetitions

## Limitations

This is only a control fixture. It does **not** implement all Superbot requirements. In particular, it does not yet model MT5 contract sizes/tick values, volume steps, swap/funding, partial exits, trailing stops, correlation budgets, a portfolio of concurrent positions, real session calendars, or a full event-sourced audit store. These must not be inferred from a passing result.

The runtime benchmark uses 2,000 small simulator calls per measured repetition. Python `tracemalloc` reports Python allocation peaks, not total process RSS. For the official resource comparison, also record process memory, CPU, disk I/O, startup, throughput, failure rate, and critical-service impact using the same workload for each candidate. The benchmark is too small to establish a production performance estimate.

## Candidate engine comparison

Do not compare engines until the same fixtures and expected event results are implemented for each candidate. Candidates currently under consideration are NautilusTrader, LEAN, and this custom baseline. Candidate-specific installation, licensing, stable-version, and resource feasibility checks remain separate gates.

## Evidence policy

Keep each generated JSON report. Record the exact Python version, machine, code revision/hash, fixture hash, run conditions, and any deviations. Do not mix these synthetic-fixture results with historical-market results.
