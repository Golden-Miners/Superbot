# TDD Evidence Report — M9.3 Agent Contracts, Permissions, Proposal Store, Deterministic Orchestration

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.3` ("Implement agent contracts/permissions/proposal store/deterministic orchestration").

## User journeys
- As a system operator, I want to register agent contracts with permissions, resource limits, and concurrency limits
- As a researcher, I want proposals to be created, approved, or rejected through a deterministic store
- As a system operator, I want proposals to be immutable once created (no silent edits)
- As a researcher, I want proposal state to be deterministic (pending → approved/rejected/executed)
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| AgentContract creation | `tests/unit/test_agent_contracts.py::test_agent_contract_creates` | ModuleNotFoundError | PASS | AgentContract stores agent_id, name, permissions, max_concurrent_tasks, max_cost_per_task |
| AgentRegistry creation | `tests/unit/test_agent_contracts.py::test_agent_registry_creates` | ModuleNotFoundError | PASS | AgentRegistry instantiates |
| Register agent | `tests/unit/test_agent_contracts.py::test_register_agent` | ModuleNotFoundError | PASS | Strategy registered and retrievable by name |
| Get unknown agent | `tests/unit/test_agent_contracts.py::test_get_unknown_agent` | ModuleNotFoundError | PASS | Unknown agent returns None |
| Proposal creation | `tests/unit/test_agent_contracts.py::test_proposal_creates` | ModuleNotFoundError | PASS | Proposal dataclass with proposal_id, agent_id, action, parameters, status=pending |
| Proposal store creation | `tests/unit/test_proposal_store_creates` | ModuleNotFoundError | PASS | ProposalStore instantiates |
| Register proposal | `tests/unit/test_register_proposal` | ModuleNotFoundError | PASS | Proposal registered and retrievable by ID |
| Get unknown proposal | `tests/unit/test_get_unknown_proposal` | ModuleNotFoundError | PASS | Unknown proposal returns None |
| Approve proposal | `tests/unit/test_approve_proposal` | ModuleNotFoundError | PASS | Proposal status → approved |
| Reject proposal | `tests/unit/test_reject_proposal` | ModuleNotFoundError | PASS | Proposal status → rejected |
| Approve unknown proposal | `tests/unit/test_approve_unknown_proposal` | ModuleNotFoundError | PASS | Unknown proposal raises KeyError |
| Reject unknown proposal | `tests/unit/test_reject_unknown_proposal` | ModuleNotFoundError | PASS | Unknown proposal raises KeyError |
| Deterministic proposal | `tests/unit/test_deterministic_proposal` | ModuleNotFoundError | PASS | Same inputs → identical proposal results |
| Agent registry deterministic | `tests/unit/test_agent_registry_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical agent results |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Agent contract creation | `tests/unit/test_agent_contracts.py` | unit | PASS | 610 passed, 2 skipped |
| 2 | Agent registry | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |
| 3 | Proposal store | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |
| 4 | Approve/reject proposals | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |
| 5 | Unknown proposal handling | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |
| 7 | Agent registry deterministic | `tests/unit/test_agent_contracts.py` | unit | PASS | 596 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M9.3 lines exercised by unit tests
- Intentional gap: No persistence of agent contracts or proposals — in-memory only
- Intentional gap: No integration with M9.1/M9.2 (benchmark/router) — standalone

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m9.agent_contracts'` captured before implementation. GREEN: 610 tests pass, 2 skipped, ruff clean, format clean, working tree clean.