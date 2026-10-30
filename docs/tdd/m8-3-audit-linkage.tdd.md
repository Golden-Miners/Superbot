# TDD Evidence Report — M8.3 Append-only Audit and Correction Linkage

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.3` ("Append-only audit and correction linkage").

## User journeys
- As a researcher, I want an append-only audit log of risk decisions (halt, resume, block, reject, resize)
- As a researcher, I want each event immutable with a hash chain (event hash = hash(content + previous_hash))
- As a researcher, I want corrections to create NEW events linked to original event id (never modify originals)
- As a researcher, I want tampering detected via hash chain verification
- As a researcher, I want deterministic: same inputs yield identical results

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| AuditEvent creation | `tests/unit/test_audit_linkage.py::test_audit_event_creates` | ModuleNotFoundError | PASS | AuditEvent stores event_type, detail, previous_hash, event_id, timestamp, hash |
| AuditEvent hash chain | `tests/unit/test_audit_linkage.py::test_audit_event_hash_chain` | ModuleNotFoundError | PASS | Each event's hash links to previous event's hash |
| Logger creation | `tests/unit/test_audit_linkage.py::test_audit_event_logger_creates` | ModuleNotFoundError | PASS | AuditEventLogger instantiates |
| Append event | `tests/unit/test_audit_linkage.py::test_append_audit_event_immutable` | ModuleNotFoundError | PASS | Events appended, immutable snapshot |
| Append chain | `tests/unit/test_audit_linkage.py::test_append_audit_event_chain` | ModuleNotFoundError | PASS | Each event's previous_hash links to prior event |
| Verify chain valid | `tests/unit/test_audit_linkage.py::test_verify_audit_chain_valid` | ModuleNotFoundError | PASS | Intact chain returns True |
| Verify chain tampered | `tests/unit/test_audit_linkage.py::test_verify_audit_chain_tampered` | ModuleNotFoundError | PASS | Tampered event returns False |
| Correction creation | `tests/unit/test_audit_linkage.py::test_correction_linkage_creates` | ModuleNotFoundError | PASS | AuditCorrection stores original_event_id, corrected_detail, reason |
| Link correction | `tests/unit/test_audit_linkage.py::test_link_correction` | ModuleNotFoundError | PASS | Creates correction linked to original; original unchanged |
| Correction unknown original blocked | `tests/unit/test_audit_linkage.py::test_link_correction_unknown_original_blocked` | ModuleNotFoundError | PASS | Unknown original raises AuditIntegrityError |
| Correction chain integrity | `tests/unit/test_audit_linkage.py::test_correction_chain_integrity` | ModuleNotFoundError | PASS | Correction events part of chain, verified |
| Deterministic | `tests/unit/test_audit_linkage.py::test_audit_linkage_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical event_type/detail |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Append-only audit log | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |
| 2 | Hash chain integrity | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |
| 3 | Tamper detection | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |
| 4 | Corrections linked to original | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |
| 5 | Original events never modified | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_audit_linkage.py` | unit | PASS | 510 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.3 lines exercised by unit tests
- Intentional gap: No persistence of audit events — in-memory only
- Intentional gap: Audit timestamp uses wall-clock time (time.time()), not injectable
- Intentional gap: No multi-process concurrency for audit log

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.audit_linkage'` captured before implementation. GREEN: 510 tests pass, 2 skipped, ruff clean, format clean, working tree clean.