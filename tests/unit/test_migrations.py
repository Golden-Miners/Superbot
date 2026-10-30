"""RED tests for M8.2 — Versioned migrations and old experiment readability.

Tests define:
- MigrationService: tracks applied schema versions, applies migrations in order
- Migration: a single versioned migration with up/down (forward/backward) functions
- MigrationRecord: record of an applied migration (version, applied_at, success)
- Migrations applied in ascending version order, each at most once
- Old experiment readability: can read experiment data written under an older schema
- Schema evolution: adding a column doesn't break reading old rows
- Missing/invalid migration files block rather than silently skipping
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/DB activity
"""

from __future__ import annotations

from superbot.persistence.migrations import (
    ExperimentRecord,
    ExperimentStore,
    Migration,
    MigrationResult,
    MigrationService,
    apply_migration,
    check_migration_status,
    read_experiment,
    record_experiment,
    rollback_migration,
)


def test_migration_creates():
    """Migration can be created with version and up/down functions."""
    m = Migration(version=1, up=lambda: None, down=lambda: None)
    assert m.version == 1


def test_migration_service_creates():
    """MigrationService can be created."""
    service = MigrationService()
    assert service is not None


def test_apply_migration_records():
    """apply_migration records and applies a migration in order."""
    service = MigrationService()
    applied = []
    service.register_migration(
        Migration(version=1, up=lambda: applied.append("up1"), down=lambda: applied.append("down1"))
    )
    result = apply_migration(service, 1)
    assert result.version == 1
    assert result.success is True
    assert applied == ["up1"]


def test_apply_migration_twice_blocked():
    """Applying the same migration twice is blocked (idempotent guard)."""
    service = MigrationService()
    applied = []
    service.register_migration(
        Migration(version=1, up=lambda: applied.append("up1"), down=lambda: applied.append("down1"))
    )
    apply_migration(service, 1)
    result = apply_migration(service, 1)
    assert result.success is False
    assert applied == ["up1"]


def test_migrations_applied_in_order():
    """Migrations are applied in ascending version order."""
    service = MigrationService()
    order = []
    service.register_migration(
        Migration(version=2, up=lambda: order.append(2), down=lambda: order.append(2))
    )
    service.register_migration(
        Migration(version=1, up=lambda: order.append(1), down=lambda: order.append(1))
    )
    service.register_migration(
        Migration(version=3, up=lambda: order.append(3), down=lambda: order.append(3))
    )
    apply_migration(service, 1)
    apply_migration(service, 2)
    apply_migration(service, 3)
    assert order == [1, 2, 3]


def test_migration_status():
    """check_migration_status reports applied versions."""
    service = MigrationService()
    service.register_migration(Migration(version=1, up=lambda: None, down=lambda: None))
    service.register_migration(Migration(version=2, up=lambda: None, down=lambda: None))
    apply_migration(service, 1)
    status = check_migration_status(service)
    assert status[1] is True
    assert status[2] is False


def test_rollback_migration():
    """rollback_migration reverts the last applied migration."""
    service = MigrationService()
    applied = []
    service.register_migration(
        Migration(version=1, up=lambda: applied.append("up1"), down=lambda: applied.append("down1"))
    )
    apply_migration(service, 1)
    result = rollback_migration(service, 1)
    assert result.success is True
    assert applied == ["up1", "down1"]


def test_rollback_not_applied_blocked():
    """Rolling back a not-applied migration is blocked."""
    service = MigrationService()
    service.register_migration(Migration(version=1, up=lambda: None, down=lambda: None))
    result = rollback_migration(service, 1)
    assert result.success is False


def test_experiment_record_creates():
    """ExperimentRecord can be created."""
    er = ExperimentRecord(
        experiment_id="exp_1",
        strategy_name="trend_follow",
        parameters={"window": 20},
        metrics={"pf": "1.5", "sharpe": "1.2"},
        created_at="2026-01-01",
        schema_version=1,
    )
    assert er.experiment_id == "exp_1"
    assert er.schema_version == 1


def test_experiment_store_creates():
    """ExperimentStore can be created."""
    store = ExperimentStore()
    assert store is not None


def test_record_and_read_experiment():
    """record_experiment then read_experiment returns the same data."""
    store = ExperimentStore()
    record_experiment(
        store,
        experiment_id="exp_1",
        strategy_name="trend_follow",
        parameters={"window": 20},
        metrics={"pf": "1.5", "sharpe": "1.2"},
        schema_version=1,
    )
    result = read_experiment(store, "exp_1")
    assert result is not None
    assert result["strategy_name"] == "trend_follow"
    assert result["parameters"]["window"] == 20
    assert result["metrics"]["pf"] == "1.5"


def test_read_unknown_experiment():
    """read_experiment returns None for unknown experiment id."""
    store = ExperimentStore()
    assert read_experiment(store, "nonexistent") is None


def test_read_old_schema_experiment():
    """Reading an experiment written under an old schema still works (backward compat)."""
    store = ExperimentStore()
    # Old schema: no 'risk' column
    record_experiment(
        store,
        experiment_id="exp_old",
        strategy_name="structure_liq",
        parameters={"lookback": 50},
        metrics={"pf": "2.0"},
        schema_version=1,
    )
    result = read_experiment(store, "exp_old")
    assert result is not None
    assert result["strategy_name"] == "structure_liq"
    assert result["schema_version"] == 1


def test_migration_deterministic():
    """Same inputs yield identical migration results."""
    s1 = MigrationService()
    s2 = MigrationService()
    s1.register_migration(Migration(version=1, up=lambda: None, down=lambda: None))
    s2.register_migration(Migration(version=1, up=lambda: None, down=lambda: None))
    r1 = apply_migration(s1, 1)
    r2 = apply_migration(s2, 1)
    assert r1.success == r2.success
    assert r1.version == r2.version


def test_migration_result_creates():
    """MigrationResult can be created."""
    mr = MigrationResult(version=1, success=True, applied_at="2026-01-01T00:00:00")
    assert mr.version == 1
    assert mr.success is True
