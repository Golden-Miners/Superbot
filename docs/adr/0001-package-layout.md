# ADR-001: Python package and test layout

**Status:** Accepted  
**Date:** 2026-10-28  
**Scope:** M1.1 — source/package/test layout

## Decision

Use a standard Python `src` layout:

```
C:\SuperBot\
  pyproject.toml
  src/
    superbot/
      __init__.py
      config.py
      contracts/
      data/
      simulation/
      risk/
      validation/
      strategy/
      audit/
      db/
      scheduler/
      agents/
      ui/
  tests/
    unit/
    integration/
  docs/adr/
  AGENTS.md, PRD.md, context.md, architecture.md, rules.md, task.md, schema.md, design.md, Debug.md, memory.md, agents.md, START_PROMPT.md, README.md
```

- `pyproject.toml` declares the project (setuptools backend, `where = ["src"]`), pytest with `testpaths = ["tests"]` and `pythonpath = ["src"]`, and ruff (line-length 100).
- No runtime dependencies beyond the Python standard library for the foundation; optional dev tooling (pytest, ruff) declared in `[project.optional-dependencies] dev`.
- Tests live outside `src/` so they are not shipped with the package and so the package imports cleanly without test fixtures on the path.

## Rationale

- Keeps application code under `src/superbot/`, separated from specs, config, tests, and ADRs at the repository root.
- `src` layout avoids import ambiguity between the installed package and a root-level `superbot/` directory.
- pytest `pythonpath = ["src"]` lets tests run without `pip install -e .`, keeping the feedback loop local and offline (no network at test time).
- Matches Python-first, Windows-native, local-first principles (PRD §2, §14; architecture §2).
- Future modules (contracts, data, simulation, risk, validation, strategy, audit, db, scheduler, agents, ui) map directly to architecture.md §3 module boundaries, so the layout grows with the design without a later restructure.

## Alternatives considered

- Flat layout (`superbot/` at repo root): rejected because it mixes application code with root specification/config files and risks import collisions with the repo root.
- `pyproject.toml` without `pythonpath`, requiring editable install: rejected because it adds a network/pip step to the test loop and the foundation must run offline.

## Consequences

- New modules are added under `src/superbot/<domain>/`.
- New tests are added under `tests/unit/` or `tests/integration/`.
- Layout decision is recorded here; any later restructure requires a new ADR and migration of imports/tests.
