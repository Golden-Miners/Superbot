# TDD Evidence Report — M10.4 Alerts, operator actions and audit traces

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M10.4` ("Alerts, operator actions and audit traces").

## User journeys
- As a system operator, I want alerts fired when metrics cross configured thresholds, with ranked severity (INFO/WARN/ERROR/CRITICAL)
- As a system operator, I want cooldown windows to prevent alert storms from repeated threshold breaches
- As a system operator, I want to acknowledge and resolve alerts, tracking their lifecycle
- As a system operator, I want operator actions (restart, scale, etc.) logged with operator, target, and timestamp
- As a system operator, I want an append-only audit trail with hash-chain integrity so all events are tamper-evident
- As a system operator, I want all alert/audit decisions deterministic — same inputs → identical results
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| AlertSeverity enum | `tests/unit/test_alerts.py::test_alert_severity_enum` | ModuleNotFoundError | PASS | INFO/WARN/ERROR/CRITICAL with ranked order |
| Alert creation | `tests/unit/test_alerts.py::test_alert_creates` | ModuleNotFoundError | PASS | Stores id, severity, message, resource, timestamp, ack/resolved flags |
| AlertManager creation | `tests/unit/test_alerts.py::test_alert_manager_creates` | ModuleNotFoundError | PASS | Instantiates with empty rules |
| Add rule + fire alert | `tests/unit/test_alerts.py::test_add_rule_and_fire` | ModuleNotFoundError | PASS | Metric above threshold → alert fired |
| No alert below threshold | `tests/unit/test_alerts.py::test_no_alert_when_below_threshold` | ModuleNotFoundError | PASS | Metric below threshold → no alert |
| Acknowledge alert | `tests/unit/test_alerts.py::test_acknowledge_alert` | ModuleNotFoundError | PASS | acknowledged=True after ack |
| Acknowledge unknown alert | `tests/unit/test_alerts.py::test_acknowledge_unknown_alert` | ModuleNotFoundError | PASS | Unknown id → acknowledged=False |
| Resolve alert | `tests/unit/test_alerts.py::test_resolve_alert` | ModuleNotFoundError | PASS | resolved=True after resolve |
| Cooldown prevents duplicates | `tests/unit/test_alerts.py::test_cooldown_prevents_duplicate_alerts` | ModuleNotFoundError | PASS | Re-fire within cooldown → alert_fired=False |
| Deterministic alert | `tests/unit/test_alerts.py::test_alert_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| OperatorAction creation | `tests/unit/test_alerts.py::test_operator_action_creates` | ModuleNotFoundError | PASS | Stores id, type, target, operator, timestamp, status |
| OperatorActionLog creation | `tests/unit/test_alerts.py::test_operator_action_log_creates` | ModuleNotFoundError | PASS | Instantiates |
| Record operator action | `tests/unit/test_alerts.py::test_record_operator_action` | ModuleNotFoundError | PASS | Action stored and retrievable |
| Get unknown action | `tests/unit/test_alerts.py::test_get_unknown_action` | ModuleNotFoundError | PASS | Unknown id → None |
| OperatorActionResult creation | `tests/unit/test_alerts.py::test_operator_action_result_creates` | ModuleNotFoundError | PASS | Stores action_id, success, result, error |
| AuditEvent creation | `tests/unit/test_alerts.py::test_audit_event_creates` | ModuleNotFoundError | PASS | Stores id, type, actor, target, timestamp, details, hash |
| AuditTrail creation | `tests/unit/test_alerts.py::test_audit_trail_creates` | ModuleNotFoundError | PASS | Instantiates |
| Record audit event | `tests/unit/test_alerts.py::test_record_audit_event` | ModuleNotFoundError | PASS | Event appended with integrity hash |
| Audit trail append-only | `tests/unit/test_alerts.py::test_audit_trail_append_only` | ModuleNotFoundError | PASS | Frozen dataclass prevents mutation |
| Verify chain valid | `tests/unit/test_alerts.py::test_verify_audit_chain_valid` | ModuleNotFoundError | PASS | Unbroken chain → True |
| Verify chain tampered | `tests/unit/test_alerts.py::test_verify_audit_chain_tampered` | ModuleNotFoundError | PASS | Tampered event → False |
| Convenience functions | `test_fire_alert_function`, `test_acknowledge_alert_function`, `test_resolve_alert_function`, `test_record_operator_action_function`, `test_record_audit_event_function`, `test_evaluate_rules_function`, `test_verify_audit_chain_function` | ModuleNotFoundError | PASS | Module-level wrappers work |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Ranked alert severity | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |
| 2 | Rule-based alert firing + cooldown | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |
| 3 | Ack/resolve lifecycle | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |
| 4 | Operator action logging | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |
| 5 | Append-only audit trail with hash chain | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_alerts.py` | unit | PASS | 834 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M10.4 lines exercised by unit tests
- Intentional gap: no persistence — alerts/actions/audit in-memory only
- Intentional gap: no notification dispatch (email, pager, webhook) — alerting is in-memory only
- Intentional gap: no integration with M10.2 telemetry — alert evaluation is manual (caller passes metrics dict)

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m10.alerts'` captured before implementation. GREEN: 834 tests pass, 2 skipped, ruff clean, format clean, working tree clean.