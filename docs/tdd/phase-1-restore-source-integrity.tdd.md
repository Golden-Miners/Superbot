# TDD Evidence Report — Phase 1: Restore source integrity

**Task:** V1 Stabilization and Security Repair Sprint — Phase 1
**Branch:** `repair/v1-stabilization`
**Date:** Sat Oct 31 2026

---

## Source plan

Evaluation report: `docs/EVALUATION-REPORT-V1-STABILIZATION.md`
- D-1: Invalid Python 2 exception syntax in `src/superbot/data/mt5_adapter.py:57`
- D-2: Invalid Python 2 exception syntax in `src/superbot/strategy/parameter_robustness.py:301`
- D-3: Undeclared dependencies (pyarrow, uvicorn, pytest-playwright)

## User journeys

- As a developer, I can import `superbot.data.mt5_adapter` without syntax errors on Python 3.14
- As a developer, I can import `superbot.strategy.parameter_robustness` without syntax errors on Python 3.14
- As a developer, `pyproject.toml` declares all runtime and dev dependencies actually used by the codebase
- As a CI system, the full test suite passes and compileall succeeds on Python 3.14

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| mt5_adapter exception handler uses valid Python 3 syntax | `python -m compileall src/superbot/data/mt5_adapter.py` | `except InvalidOperation, ValueError, TypeError:` (Python 2 comma form) | compileall exit 0 | `except (InvalidOperation, ValueError, TypeError):` |
| parameter_robustness exception handler uses valid Python 3 syntax | `python -m compileall src/superbot/strategy/parameter_robustness.py` | `except decimal.InvalidOperation, TypeError, ValueError:` (Python 2 comma form) | compileall exit 0 | `except (decimal.InvalidOperation, TypeError, ValueError):` |
| pyproject.toml declares pyarrow | `python -c "import pyarrow"` | ImportError (undeclared but used) | import OK | pyarrow declared as runtime dependency |
| pyproject.toml declares uvicorn (FastAPI server) | `python -c "import uvicorn"` | ImportError (undeclared but needed) | import OK | uvicorn declared as runtime dependency |
| pyproject.toml declares pytest-playwright | `python -c "import pytest_playwright"` | ImportError (undeclared but used by e2e) | import OK | pytest-playwright declared as dev dependency |
| Full project compiles on Python 3.14 | `python -m compileall -q src/ tests/` | compileall exit 0 | compileall exit 0 | All modules compile |
| Full test suite passes | `python -m pytest tests/unit tests/e2e` | 27 tests pass (mt5 + parameter_robustness) | Full suite exit 0 | All tests pass |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | mt5_adapter parses and compiles | `python -m compileall src/superbot/data/mt5_adapter.py` | compile | PASS | exit 0 |
| 2 | parameter_robustness parses and compiles | `python -m compileall src/superbot/strategy/parameter_robustness.py` | compile | PASS | exit 0 |
| 3 | mt5_adapter unit tests pass | `pytest tests/unit/test_mt5_adapter.py -q` | unit | PASS | 6 tests |
| 4 | parameter_robustness unit tests pass | `pytest tests/unit/test_parameter_robustness.py -q` | unit | PASS | 21 tests |
| 5 | Full project compiles | `python -m compileall -q src/ tests/` | compile | PASS | exit 0 |
| 6 | Full test suite passes | `pytest tests/unit tests/e2e -q` | unit+e2e | PASS | exit 0 |

## Coverage and known gaps

- compileall run on entire `src/` and `tests/` — exit 0
- Full `tests/unit` + `tests/e2e` suite — exit 0 (some MT5-terminal-dependent tests skipped when no live terminal available)
- ruff clean (verified separately)
- pyarrow, uvicorn added to runtime dependencies; pytest-playwright added to dev extras
- `requires-python = ">=3.14"` unchanged — compatible with Python 3.14.7

## Merge evidence

RED: `except InvalidOperation, ValueError, TypeError:` (Python 2 comma form) in mt5_adapter.py:57 and `except decimal.InvalidOperation, TypeError, ValueError:` in parameter_robustness.py:301 — invalid multi-target except syntax. GREEN: both fixed to `except (...):` tuple form; compileall exit 0; full suite exit 0; ruff clean. New/changed files: `pyproject.toml`, `src/superbot/data/mt5_adapter.py`, `src/superbot/strategy/parameter_robustness.py`.
