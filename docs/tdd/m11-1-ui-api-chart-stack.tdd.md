# TDD Evidence Report — M11.1 Select UI/API/chart stack using inspection + ADR

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M11.1` ("Select UI/API/chart stack using inspection + ADR").

## User journeys
- As a system operator, I want a documented UI/API/chart stack selection for the local quant dashboard, so the frontend tech choices are deliberate and reviewed
- As a system operator, I want the stack to be Python-first, localhost-only, no build step, and offline-capable, so it matches the project's local-first principles
- As a system operator, I want the decision recorded in an ADR with rationale, alternatives considered, consequences, and inspected versions/licenses, so the decision is auditable
- As a system operator, I want the stack exposed as a testable Python constant, so the selection is verified by tests, not just documentation
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| UIStack creation | `tests/unit/test_ui_stack.py::test_ui_stack_creates` | ModuleNotFoundError | PASS | Stores ui_framework, api_framework, chart_library, packaging |
| UIStackSelection creation | `tests/unit/test_ui_stack.py::test_ui_stack_selection_creates` | ModuleNotFoundError | PASS | Stores stack + rationale |
| StackDecision records version/license | `tests/unit/test_ui_stack.py::test_stack_decision_records_version_license` | ModuleNotFoundError | PASS | Records inspected version, license, runtime, requirements, suitability, accept, reason |
| load_ui_stack returns selection | `tests/unit/test_ui_stack.py::test_load_ui_stack_returns_selection` | ModuleNotFoundError | PASS | Returns non-empty stack with all layers |
| ui_stack module constant | `tests/unit/test_ui_stack.py::test_ui_stack_constant` | ModuleNotFoundError | PASS | Streamlit/FastAPI/Plotly/pip |
| load_adr exists | `tests/unit/test_ui_stack.py::test_load_adr_exists` | ModuleNotFoundError | PASS | Reads ADR file; contains stack names + "accepted" |
| ADR status accepted | `tests/unit/test_ui_stack.py::test_adr_has_status_accepted` | ModuleNotFoundError | PASS | ADR has Status: Accepted |
| ADR documents rationale | `tests/unit/test_ui_stack.py::test_adr_documents_rationale` | ModuleNotFoundError | PASS | ADR contains "rationale" |
| ADR documents alternatives | `tests/unit/test_ui_stack.py::test_adr_documents_alternatives` | ModuleNotFoundError | PASS | ADR contains "alternative" |
| ADR documents consequences | `tests/unit/test_ui_stack.py::test_adr_documents_consequences` | ModuleNotFoundError | PASS | ADR contains "consequence" |
| ADR records version | `tests/unit/test_ui_stack.py::test_adr_records_inspected_version` | ModuleNotFoundError | PASS | ADR contains "version" |
| ADR records license | `tests/unit/test_ui_stack.py::test_adr_records_inspected_license` | ModuleNotFoundError | PASS | ADR contains "license" |
| Deterministic stack | `tests/unit/test_ui_stack.py::test_ui_stack_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical stack |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Stack selection module + constant | `tests/unit/test_ui_stack.py` | unit | PASS | 847 passed, 2 skipped |
| 2 | ADR exists with Status: Accepted | `tests/unit/test_ui_stack.py` | unit | PASS | 847 passed, 2 skipped |
| 3 | ADR documents rationale/alternatives/consequences | `tests/unit/test_ui_stack.py` | unit | PASS | 847 passed, 2 skipped |
| 4 | ADR records versions/licenses | `tests/unit/test_ui_stack.py` | unit | PASS | 847 passed, 2 skipped |
| 5 | Deterministic selection | `tests/unit/test_ui_stack.py` | unit | PASS | 847 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M11.1 lines exercised by unit tests
- Intentional gap: no actual UI/API/chart code implemented yet — M11.1 is selection + ADR only; implementation happens in M11.2+
- Intentional gap: `tradingview/lightweight-charts` evaluated and rejected in ADR for V1 (requires JS build step); may be reconsidered later with evidence
- Stack is declared in code (`ui_stack` constant) and documented in ADR; both are verified by tests

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m11.ui_stack'` captured before implementation. GREEN: 847 tests pass, 2 skipped, ruff clean, format clean, working tree clean.