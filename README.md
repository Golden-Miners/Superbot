# Superbot OpenCode Specification Pack

This pack is the working specification for a new, standalone, local-first AI trading research and simulation application called **Superbot**. It is not based on GoldMasters.

## Start here

1. Extract the pack into the root of the new Superbot repository.
2. Preserve the requested files, including `AGENTS.md` and `START_PROMPT.md`.
3. Open OpenCode from the repository root.
4. Paste the complete prompt in `START_PROMPT.md`.
5. Require OpenCode to inspect the existing repository and installed tools before changing application code.

## Files

- `AGENTS.md`: OpenCode-discovered project instructions and links to detailed specifications.
- `PRD.md`: product requirements, scope, lifecycle and acceptance gates.
- `agents.md`: application agents, authority boundaries and orchestration.
- `rules.md`: non-negotiable development and safety rules, including the ECC build loop.
- `memory.md`: durable project facts and memory-writing protocol.
- `architecture.md`: target architecture and integration boundaries.
- `Debug.md`: debugging, incident and failure-learning protocol.
- `design.md`: dashboard and user-experience requirements.
- `task.md`: milestone-based implementation plan and status ledger.
- `schema.md`: canonical domain contracts and persisted-record requirements.
- `context.md`: current project state, confirmed decisions, unresolved decisions and baseline evidence.
- `START_PROMPT.md`: copy-paste prompt to begin implementation.

## Source-of-truth policy

The user's confirmed decisions and measured evidence in `context.md` take precedence over speculative implementation defaults. Where a choice is not settled, the documents mark it **OPEN**. OpenCode must investigate, present evidence, propose a bounded option, and record an Architecture Decision Record (ADR) before locking it. It may implement only non-blocking scaffolding while an unrelated choice is open.

## Current evidence boundary

The user's local baseline POC passed seven synthetic correctness checks. No full engine has been installed or benchmarked on their laptop. Do not claim that the laptop, MT5 connection, PostgreSQL, local model runtime, candidate engines, or an end-to-end application has been tested unless new reproducible evidence is recorded.
