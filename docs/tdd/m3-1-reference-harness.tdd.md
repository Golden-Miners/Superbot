# TDD Evidence Report — M3.1 Event-by-event reference harness

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.1` ("Extend custom baseline fixtures into event-by-event reference harness") and the M3 engine POC plan (custom Python baseline is the comparison control).

## User journeys
- As a researcher, I want an event-by-event reference harness built on the custom baseline POC so candidate engines (NautilusTrader, LEAN) can be compared against a known-correct reference.
- As a researcher, I want deterministic next-bar-open entry, stop-first ambiguous SL/TP, stop-gap worse-open fill, explicit cost accounting, and deterministic risk gates preserved from the POC.
- As a researcher, I want the harness to emit comparable event records (entries, exits, costs, reason codes) that candidate engines must match event-for-event.
- As a researcher, I want the harness to be stdlib-only with no import-time network/MT5/database/model activity so it can run in any environment.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Next-bar-open entry | `tests/unit/test_reference_harness.py::test_harness_next_bar_open_entry` | ModuleNotFoundError | PASS | Entry at next bar open, correct price/timestamp |
| Stop-first ambiguous same-bar | `test_harness_stop_first_ambiguous_same_bar` | ModuleNotFoundError | PASS | Both-hit bar resolves to stop |
| Stop-gap worse open | `test_harness_stop_gap_worse_open` | ModuleNotFoundError | PASS | Gap fill at worse opening price |
| Explicit costs | `test_harness_explicit_costs` | ModuleNotFoundError | PASS | spread + 2x commission deducted |
| Deterministic repeatability | `test_harness_deterministic_repeatability` | ModuleNotFoundError | PASS | Identical inputs → identical event sequence |
| Risk gate rejects | `test_harness_risk_gate_rejects` | ModuleNotFoundError | PASS | `portfolio_open_risk_cap` reason code |
| Invalid side rejected | `test_harness_invalid_side_rejected` | ModuleNotFoundError | PASS | `ReferenceHarnessError` raised |

## Test specification
| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Entry at next bar open with correct price/timestamp | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite, TEST_EXIT:True |
| 2 | Stop-first on ambiguous same-bar SL/TP | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |
| 3 | Stop-gap fill at worse opening price | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |
| 4 | Explicit spread/commission cost accounting | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |
| 5 | Deterministic repeatability (identical inputs → identical events) | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |
| 6 | Deterministic risk gate with reason codes | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |
| 7 | Invalid side raises `ReferenceHarnessError` | `tests/unit/test_reference_harness.py` | unit | PASS | 167-test suite |

## Coverage and known gaps
- No coverage tool configured; all M3.1 lines exercised by unit tests.
- Intentional gap: harness models a single trade only (no multi-position accounting, partial exits, swaps, trailing) — same scope as the POC. These belong to M4 (deterministic simulator).
- Intentional gap: no candidate engine comparison run yet — that's M3.3/M3.4.
- Semantics preserved exactly from `superbot_poc.py` (fixture, stop-first, stop-gap, costs, risk gates) so candidate engines have a stable reference.

## Merge evidence
Commit: `ce3d798` (M3.1 implementation + tests). RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 167 tests pass, ruff clean, format clean, `git diff --check` clean, working tree clean.
