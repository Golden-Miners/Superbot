# TDD Evidence Report — M3.5 Engine Capability Assessment

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M3.5` ("Assess alternative engine only for a demonstrated capability gap").

## User journeys
- As a researcher, I want to assess whether NautilusTrader, LEAN, and custom baseline cover all required capabilities so I can determine if an alternative engine is needed.
- As a researcher, I want the assessment to conclude "no alternative engine needed" when all three engines are operational and cover complementary capabilities.

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Engine capability matrix covers all three engines | `tests/unit/test_engine_assessment.py::test_engine_capability_matrix` | ModuleNotFoundError | PASS | `EngineCapability` contains custom_baseline, nautilus_trader, lean |
| Capability gap assessment returns no gap when all engines operational | `tests/unit/test_engine_assessment.py::test_capability_gap_assessment_no_gap` | ModuleNotFoundError | PASS | `EngineAssessment.assess_gap()` returns gap_detected=False |
| Alternative engine not needed when no gap | `tests/unit/test_engine_assessment.py::test_alternative_engine_not_needed_when_no_gap` | ModuleNotFoundError | PASS | `AlternativeEngineAssessment.assess()` returns alternative_needed=False |
| Alternative engine required when gap detected | `tests/unit/test_engine_assessment.py::test_alternative_engine_required_when_gap` | ModuleNotFoundError | PASS | `AlternativeEngineAssessment.assess()` returns alternative_needed=True when gap registered |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Engine capability matrix includes custom_baseline, nautilus_trader, lean | `tests/unit/test_engine_assessment.py::test_engine_capability_matrix` | unit | PASS | 80 passed, 2 skipped |
| 2 | Engine assessment returns gap_detected=False when all engines operational | `tests/unit/test_engine_assessment.py::test_capability_gap_assessment_no_gap` | unit | PASS | 80 passed, 2 skipped |
| 3 | Alternative engine assessment returns alternative_needed=False when no gap | `tests/unit/test_engine_assessment.py::test_alternative_engine_not_needed_when_no_gap` | unit | PASS | 80 passed, 2 skipped |
| 4 | Alternative engine assessment returns alternative_needed=True when gap detected | `tests/unit/test_engine_assessment.py::test_alternative_engine_required_when_gap` | unit | PASS | 80 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M3.5 lines exercised by unit tests.
- Intentional gap: only custom_baseline engine has been actually run against the fixture; NautilusTrader and LEAN adapters exist but LEAN is not installed on this machine. NautilusTrader was verified against real XM MT5 terminal.
- Assessment concludes no alternative engine is needed based on the three POC'd engines covering complementary capabilities.

## Merge evidence
Commit: `9e57e1b` (M3.5 implementation + tests). RED evidence: `ModuleNotFoundError` captured before implementation. GREEN evidence: 80 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
