"""RED tests for M10.4 — Alerts, operator actions and audit traces.

Tests define:
- AlertSeverity: INFO, WARN, ERROR, CRITICAL
- Alert: id, severity, message, resource, timestamp, acknowledged, resolved
- AlertRule: condition, severity, cooldown_seconds
- AlertManager: evaluate metrics against rules, fire/acknowledge/resolve alerts
- OperatorAction: id, action_type, target, operator, timestamp, status, result
- OperatorActionLog: record and retrieve operator actions
- AuditEvent: id, event_type, actor, target, timestamp, details, integrity_hash
- AuditTrail: append-only immutable audit log with hash chain
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from superbot.m10.alerts import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AuditEvent,
    AuditTrail,
    OperatorAction,
    OperatorActionLog,
    OperatorActionResult,
    acknowledge_alert,
    evaluate_rules,
    fire_alert,
    record_audit_event,
    record_operator_action,
    resolve_alert,
    verify_audit_chain,
)


def test_alert_severity_enum():
    """AlertSeverity defines ordered severity levels."""
    assert AlertSeverity.INFO.value == "info"
    assert AlertSeverity.WARN.value == "warn"
    assert AlertSeverity.ERROR.value == "error"
    assert AlertSeverity.CRITICAL.value == "critical"
    assert AlertSeverity.rank(AlertSeverity.CRITICAL) > AlertSeverity.rank(AlertSeverity.ERROR)
    assert AlertSeverity.rank(AlertSeverity.ERROR) > AlertSeverity.rank(AlertSeverity.WARN)
    assert AlertSeverity.rank(AlertSeverity.WARN) > AlertSeverity.rank(AlertSeverity.INFO)


def test_alert_creates():
    """Alert stores id, severity, message, resource, timestamp, acknowledged, resolved."""
    alert = Alert(
        alert_id="alert_1",
        severity=AlertSeverity.WARN,
        message="High CPU usage",
        resource="api_1",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    assert alert.alert_id == "alert_1"
    assert alert.severity == AlertSeverity.WARN
    assert alert.message == "High CPU usage"
    assert alert.resource == "api_1"
    assert alert.acknowledged is False
    assert alert.resolved is False


def test_alert_manager_creates():
    """AlertManager can be created with rules."""
    manager = AlertManager()
    assert manager is not None


def test_add_rule_and_fire():
    """AlertManager evaluates metrics and fires alerts when rules match."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    result = manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    assert result.alert_fired is True
    assert result.severity == AlertSeverity.WARN


def test_no_alert_when_below_threshold():
    """AlertManager does not fire when metric below threshold."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    result = manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.5})
    assert result.alert_fired is False


def test_acknowledge_alert():
    """acknowledge_alert marks an alert as acknowledged."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    alert_id = manager.active_alerts[0].alert_id
    result = manager.acknowledge(alert_id, "operator_1")
    assert result.acknowledged is True
    assert manager.active_alerts[0].acknowledged is True


def test_acknowledge_unknown_alert():
    """acknowledge_alert fails for unknown alert id."""
    manager = AlertManager()
    result = manager.acknowledge("nonexistent", "operator_1")
    assert result.acknowledged is False


def test_resolve_alert():
    """resolve_alert marks an alert as resolved."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    alert_id = manager.active_alerts[0].alert_id
    result = manager.resolve(alert_id)
    assert result.resolved is True
    assert all(a.alert_id != alert_id for a in manager.active_alerts)


def test_cooldown_prevents_duplicate_alerts():
    """AlertManager cooldown prevents re-firing the same alert within cooldown window."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
            cooldown_seconds=300,
        )
    )
    manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    len(manager.active_alerts)
    result = manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    assert result.alert_fired is False  # cooldown active


def test_alert_deterministic():
    """Same inputs yield identical alert results."""
    m1 = AlertManager()
    m2 = AlertManager()
    m1.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    m2.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    r1 = m1.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    r2 = m2.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    assert r1.alert_fired == r2.alert_fired


def test_operator_action_creates():
    """OperatorAction stores id, action_type, target, operator, timestamp, status, result."""
    action = OperatorAction(
        action_id="action_1",
        action_type="restart",
        target="worker_1",
        operator="admin",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    assert action.action_id == "action_1"
    assert action.action_type == "restart"
    assert action.target == "worker_1"
    assert action.operator == "admin"
    assert action.status == "pending"


def test_operator_action_log_creates():
    """OperatorActionLog can be created."""
    log = OperatorActionLog()
    assert log is not None


def test_record_operator_action():
    """record_operator_action adds an action to the log."""
    log = OperatorActionLog()
    action = OperatorAction(
        action_id="action_1",
        action_type="scale",
        target="worker_pool",
        operator="admin",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    log.record(action)
    retrieved = log.get_action("action_1")
    assert retrieved is not None
    assert retrieved.action_type == "scale"


def test_get_unknown_action():
    """get_action returns None for unknown action id."""
    log = OperatorActionLog()
    assert log.get_action("nonexistent") is None


def test_operator_action_result_creates():
    """OperatorActionResult stores action_id, success, result, error."""
    result = OperatorActionResult(
        action_id="action_1",
        success=True,
        result="scaled to 3 workers",
        error=None,
    )
    assert result.action_id == "action_1"
    assert result.success is True


def test_audit_event_creates():
    """AuditEvent stores id, event_type, actor, target, timestamp, details, integrity_hash."""
    trail = AuditTrail()
    event = trail.record(
        event_type="config_change",
        actor="admin",
        target="config.yaml",
        details={"key": "value"},
    )
    assert event.event_type == "config_change"
    assert event.actor == "admin"
    assert event.target == "config.yaml"
    assert event.integrity_hash != ""


def test_audit_trail_creates():
    """AuditTrail can be created."""
    trail = AuditTrail()
    assert trail is not None


def test_record_audit_event():
    """record_audit_event appends an event with hash chain."""
    trail = AuditTrail()
    event = trail.record(
        event_type="config_change",
        actor="admin",
        target="config.yaml",
        details={"key": "value"},
    )
    assert event.event_type == "config_change"
    assert event.integrity_hash != ""


def test_audit_trail_append_only():
    """AuditTrail events are immutable (frozen dataclass)."""
    trail = AuditTrail()
    trail.record(event_type="start", actor="system", target="app", details={})
    event_count = len(trail.events)
    with pytest.raises(FrozenInstanceError):
        trail.events[0].details = {"tampered": True}
    assert len(trail.events) == event_count


def test_verify_audit_chain_valid():
    """verify_audit_chain returns True for unbroken hash chain."""
    trail = AuditTrail()
    trail.record(event_type="start", actor="system", target="app", details={})
    trail.record(event_type="stop", actor="admin", target="app", details={})
    assert trail.verify_chain() is True


def test_verify_audit_chain_tampered():
    """verify_audit_chain returns False if an event is tampered."""
    trail = AuditTrail()
    trail.record(event_type="start", actor="system", target="app", details={})
    trail.record(event_type="stop", actor="admin", target="app", details={})
    # Tamper by replacing the event object's details (hash stored at record time)
    original_hash = trail.events[0].integrity_hash
    trail.events[0] = AuditEvent(
        event_id=trail.events[0].event_id,
        event_type="tampered",
        actor="system",
        target="app",
        timestamp=trail.events[0].timestamp,
        details={"tampered": True},
        integrity_hash=original_hash,
    )
    assert trail.verify_chain() is False


def test_fire_alert_function():
    """fire_alert convenience function works."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    result = fire_alert(manager, {"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    assert result.alert_fired is True


def test_acknowledge_alert_function():
    """acknowledge_alert convenience function works."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    alert_id = manager.active_alerts[0].alert_id
    result = acknowledge_alert(manager, alert_id, "operator_1")
    assert result.acknowledged is True


def test_resolve_alert_function():
    """resolve_alert convenience function works."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    manager.evaluate({"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    alert_id = manager.active_alerts[0].alert_id
    result = resolve_alert(manager, alert_id)
    assert result.resolved is True


def test_record_operator_action_function():
    """record_operator_action convenience function works."""
    log = OperatorActionLog()
    action = OperatorAction(
        action_id="action_1",
        action_type="restart",
        target="worker_1",
        operator="admin",
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    result = record_operator_action(log, action)
    assert result.success is True


def test_record_audit_event_function():
    """record_audit_event convenience function works."""
    trail = AuditTrail()
    result = record_audit_event(trail, "login", "user_1", "auth", {"status": "ok"})
    assert result.event_type == "login"
    assert result.integrity_hash != ""


def test_evaluate_rules_function():
    """evaluate_rules convenience function works."""
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="high_cpu",
            resource_type="api",
            metric="cpu_usage",
            threshold=0.8,
            severity=AlertSeverity.WARN,
        )
    )
    result = evaluate_rules(manager, {"resource_type": "api", "metric": "cpu_usage", "value": 0.9})
    assert result.alert_fired is True


def test_verify_audit_chain_function():
    """verify_audit_chain convenience function works."""
    trail = AuditTrail()
    trail.record(event_type="start", actor="system", target="app", details={})
    result = verify_audit_chain(trail)
    assert result is True
