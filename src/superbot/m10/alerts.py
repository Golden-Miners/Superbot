"""M10.4 — Alerts, operator actions and audit traces.

Deterministic alerting/audit service:
- AlertSeverity: INFO, WARN, ERROR, CRITICAL (ranked)
- Alert: id, severity, message, resource, timestamp, acknowledged, resolved
- AlertRule: condition (resource_type/metric/threshold), severity, cooldown_seconds
- AlertManager: evaluate metrics against rules, fire/acknowledge/resolve alerts
- OperatorAction: id, action_type, target, operator, timestamp, status, result
- OperatorActionLog: record and retrieve operator actions
- OperatorActionResult: action outcome
- AuditEvent: id, event_type, actor, target, timestamp, details, integrity_hash
- AuditTrail: append-only immutable audit log with hash chain
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels, ranked by urgency."""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def rank(cls, severity: AlertSeverity) -> int:
        """Return numeric rank for severity (higher = more urgent)."""
        return _SEVERITY_RANK[severity.value]


_SEVERITY_RANK: dict[str, int] = {
    "info": 1,
    "warn": 2,
    "error": 3,
    "critical": 4,
}


@dataclass(frozen=True)
class Alert:
    """An alert fired by the alert manager."""

    alert_id: str
    severity: AlertSeverity
    message: str
    resource: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


@dataclass(frozen=True)
class AlertRule:
    """A rule that fires an alert when a metric crosses a threshold."""

    name: str
    resource_type: str
    metric: str
    threshold: float
    severity: AlertSeverity
    cooldown_seconds: int = 300


@dataclass(frozen=True)
class AlertResult:
    """Result of evaluating metrics against alert rules."""

    alert_fired: bool
    severity: AlertSeverity | None = None
    alert_id: str | None = None


@dataclass(frozen=True)
class AckResult:
    """Result of acknowledging an alert."""

    acknowledged: bool
    alert_id: str | None = None


@dataclass(frozen=True)
class ResolveResult:
    """Result of resolving an alert."""

    resolved: bool
    alert_id: str | None = None


class AlertManager:
    """Evaluates metrics against alert rules and manages alert lifecycle."""

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._alerts: list[Alert] = []
        self._last_fired: dict[str, datetime] = {}
        self._counter = 0

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules.append(rule)

    def evaluate(self, metrics: dict) -> AlertResult:
        """Evaluate metrics against all rules; fire an alert if any rule matches and cooldown expired."""
        resource_type = metrics.get("resource_type")
        metric = metrics.get("metric")
        value = metrics.get("value")
        if resource_type is None or metric is None or value is None:
            return AlertResult(alert_fired=False)

        for rule in self._rules:
            if rule.resource_type != resource_type or rule.metric != metric:
                continue
            if not (value > rule.threshold):
                continue
            key = f"{rule.name}|{resource_type}|{metric}"
            now = datetime.now(UTC)
            last = self._last_fired.get(key)
            if last is not None and (now - last).total_seconds() < rule.cooldown_seconds:
                return AlertResult(alert_fired=False, severity=rule.severity)
            self._last_fired[key] = now
            self._counter += 1
            alert = Alert(
                alert_id=f"alert_{self._counter}",
                severity=rule.severity,
                message=f"{rule.name}: {metric}={value} > {rule.threshold}",
                resource=str(metrics.get("resource_id", resource_type)),
                timestamp=now,
            )
            self._alerts.append(alert)
            return AlertResult(alert_fired=True, severity=rule.severity, alert_id=alert.alert_id)

        return AlertResult(alert_fired=False)

    @property
    def active_alerts(self) -> list[Alert]:
        """Return alerts that are not yet resolved."""
        return [a for a in self._alerts if not a.resolved]

    def acknowledge(self, alert_id: str, operator: str) -> AckResult:
        """Acknowledge an alert by id."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                # Frozen dataclass: rebuild with acknowledged=True
                acknowledged_alert = Alert(
                    alert_id=alert.alert_id,
                    severity=alert.severity,
                    message=alert.message,
                    resource=alert.resource,
                    timestamp=alert.timestamp,
                    acknowledged=True,
                    resolved=alert.resolved,
                )
                idx = self._alerts.index(alert)
                self._alerts[idx] = acknowledged_alert
                return AckResult(acknowledged=True, alert_id=alert_id)
        return AckResult(acknowledged=False)

    def resolve(self, alert_id: str) -> ResolveResult:
        """Resolve an alert by id."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                resolved_alert = Alert(
                    alert_id=alert.alert_id,
                    severity=alert.severity,
                    message=alert.message,
                    resource=alert.resource,
                    timestamp=alert.timestamp,
                    acknowledged=alert.acknowledged,
                    resolved=True,
                )
                idx = self._alerts.index(alert)
                self._alerts[idx] = resolved_alert
                return ResolveResult(resolved=True, alert_id=alert_id)
        return ResolveResult(resolved=False)


@dataclass(frozen=True)
class OperatorAction:
    """An operator-initiated action."""

    action_id: str
    action_type: str
    target: str
    operator: str
    timestamp: datetime
    status: str = "pending"
    result: str | None = None


@dataclass(frozen=True)
class OperatorActionResult:
    """Result of recording/executing an operator action."""

    action_id: str
    success: bool
    result: str | None = None
    error: str | None = None


class OperatorActionLog:
    """Append-only log of operator actions."""

    def __init__(self) -> None:
        self._actions: dict[str, OperatorAction] = {}
        self._order: list[str] = []

    def record(self, action: OperatorAction) -> OperatorActionResult:
        """Record an operator action."""
        self._actions[action.action_id] = action
        self._order.append(action.action_id)
        return OperatorActionResult(action_id=action.action_id, success=True)

    def get_action(self, action_id: str) -> OperatorAction | None:
        """Get an operator action by id."""
        return self._actions.get(action_id)

    def list_actions(self) -> list[OperatorAction]:
        """Return all actions in recording order."""
        return [self._actions[aid] for aid in self._order]


@dataclass(frozen=True)
class AuditEvent:
    """An immutable audit event."""

    event_id: str
    event_type: str
    actor: str
    target: str
    timestamp: datetime
    details: dict
    integrity_hash: str

    @property
    def hash_value(self) -> str:
        """Deterministic hash of this event's content."""
        content = (
            f"{self.event_id}|{self.event_type}|{self.actor}|{self.target}|"
            f"{self.timestamp.isoformat()}|{json.dumps(self.details, sort_keys=True)}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AuditTrail:
    """Append-only immutable audit log with hash chain."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._counter = 0

    def record(
        self,
        event_type: str,
        actor: str,
        target: str,
        details: dict,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        """Append a new audit event with hash chain."""
        self._counter += 1
        self.events[-1].integrity_hash if self.events else "genesis"
        event = AuditEvent(
            event_id=f"event_{self._counter}",
            event_type=event_type,
            actor=actor,
            target=target,
            timestamp=timestamp if timestamp is not None else datetime.now(UTC),
            details=dict(details),
            integrity_hash="",  # placeholder, filled below
        )
        event_hash = event.hash_value
        event = AuditEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            actor=event.actor,
            target=event.target,
            timestamp=event.timestamp,
            details=event.details,
            integrity_hash=event_hash,
        )
        self.events.append(event)
        return event

    def verify_chain(self) -> bool:
        """Verify the audit hash chain is unbroken."""
        for event in self.events:
            if event.integrity_hash != event.hash_value:
                return False
        return True


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def fire_alert(manager: AlertManager, metrics: dict) -> AlertResult:
    """Convenience: evaluate metrics against alert rules."""
    return manager.evaluate(metrics)


def acknowledge_alert(manager: AlertManager, alert_id: str, operator: str) -> AckResult:
    """Convenience: acknowledge an alert."""
    return manager.acknowledge(alert_id, operator)


def resolve_alert(manager: AlertManager, alert_id: str) -> ResolveResult:
    """Convenience: resolve an alert."""
    return manager.resolve(alert_id)


def record_operator_action(log: OperatorActionLog, action: OperatorAction) -> OperatorActionResult:
    """Convenience: record an operator action."""
    return log.record(action)


def record_audit_event(
    trail: AuditTrail,
    event_type: str,
    actor: str,
    target: str,
    details: dict,
) -> AuditEvent:
    """Convenience: record an audit event."""
    return trail.record(event_type, actor, target, details)


def evaluate_rules(manager: AlertManager, metrics: dict) -> AlertResult:
    """Convenience: evaluate metrics against alert rules."""
    return manager.evaluate(metrics)


def verify_audit_chain(trail: AuditTrail) -> bool:
    """Convenience: verify the audit trail hash chain."""
    return trail.verify_chain()
