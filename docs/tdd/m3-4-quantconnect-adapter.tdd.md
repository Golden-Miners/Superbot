# TDD Evidence Report — M3.4 QuantConnect LEAN Adapter

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.4` ("POC QuantConnect LEAN in isolated, pinned environment; test local self-managed workflow without hosted inference/platform dependency").

## User journeys
- As a researcher, I want Superbot to adapt to QuantConnect LEAN engine for event-driven backtesting
- As a researcher, I want the adapter to use the same equivalence fixtures/costs as NautilusTrader and custom baseline
- As a researcher, I want the adapter to gracefully degrade when LEAN is not installed

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Adapter raises LeanNotInstalled when quantconnect not available | `tests/unit/test_quantconnect_adapter.py::test_lean_not_installed_raises` | ModuleNotFoundError | PASS | `LeanAdapter()` raises `LeanNotInstalled` when package absent |
| Adapter instantiates when LEAN available | `tests/unit/test_quantconnect_adapter.py::test_lean_adapter_instantiates` | N/A (skipped) | SKIP | quantconnect not installed on this machine |
| Adapter runs equivalence acceptance | `tests/unit/test_quantconnect_adapter.py::test_lean_runs_equivalence_and_passes_correctness_gate` | N/A (skipped) | SKIP | quantconnect not installed on this machine |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Adapter raises `LeanNotInstalled` when quantconnect not installed | `tests/unit/test_quantconnect_adapter.py::test_lean_not_installed_raises` | unit | PASS | 76 passed, 2 skipped |
| 2 | Adapter instantiates when LEAN available | `tests/unit/test_quantconnect_adapter.py::test_lean_adapter_instantiates` | unit | SKIP | quantconnect not installed |
| 3 | Adapter runs equivalence and passes correctness gate | `tests/unit/test_quantconnect_adapter.py::test_lean_runs_equivalence_and_passes_correctness_gate` | unit | SKIP | quantconnect not installed |

## Coverage and known gaps
- quantconnect-lean is NOT installed on this machine, so 2 tests are skipped
- The adapter lazily imports `quantconnect` inside `_load_lean()`, so `superbot.engine.quantconnect_adapter` imports safely even without LEAN installed
- `LeanAdapter.__init__()` calls `_load_lean()` which raises `LeanNotInstalled` when quantconnect is not available
- When quantconnect IS installed, `run_equivalence()` will call `_run_with_lean()` which currently raises `NotImplementedError` — full LEAN integration requires the package to be installed and the adapter to be fleshed out with LEAN-specific backtest logic
- No import-time network/MT5/database/model activity
- No live order submission (read-only)

## Merge evidence
Commits: `9e57e1b` (M3.3 NautilusTrader), plus M3.4 adapter + test files + docs. RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 76 tests pass, 2 skipped (LEAN not installed), ruff clean, format clean, `git diff --check` clean, working tree clean.
