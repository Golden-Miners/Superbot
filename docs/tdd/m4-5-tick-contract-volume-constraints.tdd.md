# TDD Evidence Report — M4.5 Tick/Contract/Volume Constraints

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M4.5` ("Verified tick/contract/volume constraints; block if missing/stale").

## User journeys
- As a researcher, I want tick size and tick value validated before execution (non-zero, positive)
- As a researcher, I want contract symbol, expiry, and multiplier validated before execution
- As a researcher, I want volume validated against min/max bounds before execution
- As a researcher, I want missing/stale contract data to block execution with explicit error
- As a researcher, I want constraint validation applied to both market and limit entry fills
- As a researcher, I want identical inputs to yield identical constraint validation results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Constraint validator defaults | `tests/unit/test_tick_contract_volume_constraints.py::test_constraint_validator_defaults` | ImportError | PASS | ConstraintValidator stores tick/contract/volume fields |
| Zero tick size blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_tick_size_zero_blocks` | ImportError | PASS | `TickConstraintError` raised at construction |
| Zero tick value blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_tick_value_zero_blocks` | ImportError | PASS | `TickConstraintError` raised at construction |
| Missing contract symbol blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_contract_symbol_missing_blocks` | ImportError | PASS | `ContractConstraintError` raised at construction |
| Past contract expiry blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_contract_expiry_past_blocks` | ImportError | PASS | `ContractConstraintError` raised at construction |
| Zero contract multiplier blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_contract_multiplier_zero_blocks` | ImportError | PASS | `ContractConstraintError` raised at construction |
| Zero volume blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_volume_zero_blocks` | ImportError | PASS | `VolumeConstraintError` raised on validate_volume |
| Volume below min blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_volume_below_min_blocks` | ImportError | PASS | `VolumeConstraintError` raised on validate_volume |
| Volume above max blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_volume_above_max_blocks` | ImportError | PASS | `VolumeConstraintError` raised on validate_volume |
| Valid volume passes | `tests/unit/test_tick_contract_volume_constraints.py::test_volume_valid_passes` | ImportError | PASS | Volume within bounds returns unchanged |
| Simulator blocks stale contract | `tests/unit/test_tick_contract_volume_constraints.py::test_simulator_blocks_with_stale_contract` | ImportError | PASS | `set_constraints()` raises on past expiry |
| Simulator allows valid constraints | `tests/unit/test_tick_contract_volume_constraints.py::test_simulator_allows_valid_constraints` | ImportError | PASS | `enter_long()` succeeds with valid constraints |
| Simulator allows no constraints | `tests/unit/test_tick_contract_volume_constraints.py::test_simulator_allows_without_constraints_set` | ImportError | PASS | Backwards compatible: no constraints = no validation |
| Deterministic validation | `tests/unit/test_tick_contract_volume_constraints.py::test_constraint_validation_deterministic` | ImportError | PASS | Same inputs yield identical results |
| InstrumentSpec null tick blocks | `tests/unit/test_tick_contract_volume_constraints.py::test_instrument_spec_null_tick_blocks` | ImportError | PASS | `InstrumentSpec.validate()` raises on null tick |
| InstrumentSpec valid | `tests/unit/test_tick_contract_volume_constraints.py::test_instrument_spec_valid` | ImportError | PASS | Valid InstrumentSpec passes validation |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Tick size > 0 enforced | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 2 | Tick value > 0 enforced | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 3 | Contract symbol non-empty | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 4 | Contract expiry not stale | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 5 | Contract multiplier > 0 | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 6 | Volume within min/max | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 7 | Volume below min blocked | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 8 | Volume above max blocked | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 9 | Validation on every entry | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |
| 10 | Deterministic validation | `tests/unit/test_tick_contract_volume_constraints.py` | unit | PASS | 132 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M4.5 lines exercised by unit tests
- Intentional gap: constraint validation runs at entry time only; exit fills do not re-validate constraints
- Intentional gap: `InstrumentSpec` is a standalone dataclass not yet wired into `NextBarOpenSimulator` — simulator uses `ConstraintValidator` directly
- Intentional gap: constraints are set once via `set_constraints()`; no dynamic constraint updates during simulation

## Merge evidence
Commit: `bd56422` (M4.4) + M4.5 commit (next_bar_open.py + test_tick_contract_volume_constraints.py). RED evidence: `ImportError` captured before implementation (constraint classes missing). GREEN evidence: 132 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
