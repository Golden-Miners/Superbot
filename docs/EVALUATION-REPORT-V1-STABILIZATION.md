# V1 Stabilization and Security Repair Sprint — Evaluation Report

**Date:** Sat Oct 31 2026
**Branch:** `repair/v1-stabilization` (from `master` @ `78edf30`)
**Repository:** C:\SuperBot
**Status:** Stopping feature development; prioritizing defect repairs

---

## Evaluation Summary

Independent evaluation identified release-blocking defects in the Superbot V1 codebase. Feature development is stopped. Repairs are organized into phases:

- **Phase 0:** Preserve baseline, create repair branch, record this report (in progress).
- **Phase 1:** Restore source integrity — fix invalid exception handlers, audit dependencies, declare missing deps, compileall + tests.
- **Phase 2:** Security fixes — header-based auth removal, server-issued sessions, per-route authorization, secret serialization removal.
- **Phase 3:** Backup security — disable custom stream cipher, use maintained authenticated encryption, ADR for key management, tamper/wrong-key tests.
- **Phase 4:** Operational correctness — real service probes, synthetic-vs-live labels, real job-state transitions, settings validation, VPN doc correction.
- **Phase 5:** Cross-component integration — connect dashboards to real API outputs, integrate risk services with simulator, real PostgreSQL persistence, background-worker lifecycle.

No task is marked DONE without reproducible evidence. M11 and M12 are NOT marked complete until operational acceptance criteria are met.

---

## Defects Found

### D-1: Invalid Python 2 exception syntax — `src/superbot/data/mt5_adapter.py:57`

```python
    except InvalidOperation, ValueError, TypeError:
        return None
```

Python 2 multi-exception syntax `except X, Y:` is invalid in Python 3.14+. The module cannot be imported/executed. Fix: `except (InvalidOperation, ValueError, TypeError):`.

### D-2: Invalid Python 2 exception syntax — `src/superbot/strategy/parameter_robustness.py:301`

```python
        except decimal.InvalidOperation, TypeError, ValueError:
            return False
```

Same Python 2 multi-exception syntax. Invalid in Python 3.14+. Fix: `except (decimal.InvalidOperation, TypeError, ValueError):`.

### D-3: Client-supplied authorization header — `src/superbot/m11/api.py`

`_operator_role(request)` reads `X-Operator-Role` header to authorize sensitive settings changes. A client can forge this header to escalate privileges. Authorization must be enforced server-side via server-issued, unpredictable sessions.

### D-4: Secret serialization in API — `src/superbot/m11/api.py`

`settings_profiles(include_secrets=...)` can return secret values, and profiles carry `secret`/`secret_redacted` fields. Secret values must never be serialized by any API endpoint.

### D-5: Custom SHA-256 stream cipher for backups — `src/superbot/persistence/backup.py`

`encrypt_payload`/`decrypt_payload` implement a custom SHA-256 stream cipher. This is not authenticated encryption and must not be used for real data. Must be replaced with a maintained authenticated-encryption implementation (ADR-required key management).

### D-6: Seeded healthy service states — `src/superbot/m11/api.py`

`DashboardState._seed_health()` hardcodes all components as `HEALTHY` with no actual probing. Service states must reflect real probes or UNKNOWN/NOT PROBED.

### D-7: Synthetic fixtures presented as live data throughout UI

All dashboard surfaces render deterministic fixtures labeled `internal_simulation` but lack explicit synthetic/source provenance in UI rendering. Synthetic fixtures must be explicitly distinguished from actual live service observations.

### D-8: No real job-state transitions / cancellation API without worker management

Job cancel endpoint exists but no worker management backs it. Must implement real transitions or disable cancellation API.

### D-9: Settings not validated against schemas/ranges; invalid config can replace last-known-good

Settings updates write directly without schema/range validation and without preserving last-known-good on rejection.

### D-10: VPN documentation incorrect / no actual private-access architecture test

VPN docs claim remote access via private VPN but there is no test verifying localhost-only binding or private-access architecture.

---

## Baseline State (preserved)

| Item | Value |
|---|---|
| Branch | `repair/v1-stabilization` (created from `master`) |
| HEAD | `78edf30` (Reconcile memory.md; re-stage regenerated screenshot) |
| Working tree | Clean — all user changes preserved |
| Remote | `origin` = `https://github.com/Golden-Miners/Superbot.git` (pushed) |
| Python | 3.14.7 |
| Test runner | pytest 9.1.1 |
| Linter | ruff |

---

## Plan

Proceed to Phase 1: fix D-1 and D-2, audit dependencies, declare missing extras, compileall, focused + full test suite. Stop and report evidence before Phase 2.
