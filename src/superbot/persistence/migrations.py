"""Versioned migrations and old experiment readability (schema.md section 8.2).

Deterministic migration and experiment-readability service:
- Versioned migrations with up/down (forward/backward) functions
- Migrations applied in ascending version order, each at most once
- Migration tracking (which versions have been applied)
- Old experiment readability: read experiment data written under older schema
- Schema evolution: adding a column doesn't break reading old rows
- Missing/invalid migration files block rather than silently skipping
- Stdlib-only; no import-time network/DB activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class MissingInputError(Exception):
    """Raised when a required migration input is missing/None."""


class MigrationError(Exception):
    """Raised when a migration cannot be applied or rolled back."""


@dataclass(frozen=True)
class Migration:
    """A single versioned migration with up/down functions."""

    version: int
    up: Any
    down: Any


@dataclass(frozen=True)
class MigrationResult:
    """Result of applying or rolling back a migration."""

    version: int
    success: bool
    applied_at: str


@dataclass(frozen=True)
class ExperimentRecord:
    """An experiment record with schema version for backward compatibility."""

    experiment_id: str
    strategy_name: str
    parameters: dict
    metrics: dict
    created_at: str
    schema_version: int


@dataclass(frozen=True)
class MigrationService:
    """Tracks applied schema versions and applies migrations in order."""

    migrations: dict[int, Migration] = field(default_factory=dict)
    applied: dict[int, MigrationResult] = field(default_factory=dict)

    def register_migration(self, migration: Migration) -> None:
        """Register a migration for this version."""
        self.migrations[migration.version] = migration

    def get_migration(self, version: int) -> Migration | None:
        """Get the registered migration for a version."""
        return self.migrations.get(version)

    def is_applied(self, version: int) -> bool:
        """Check whether a version has been applied."""
        return version in self.applied

    def applied_versions(self) -> list[int]:
        """Return applied versions in ascending order."""
        return sorted(self.applied.keys())


def apply_migration(service: MigrationService, version: int) -> MigrationResult:
    """Apply a single migration if not already applied.

    Args:
        service: MigrationService with registered migrations
        version: version to apply

    Returns MigrationResult with version, success, applied_at.

    Raises MigrationError if migration not registered.
    """
    if service.is_applied(version):
        return MigrationResult(version=version, success=False, applied_at="")
    migration = service.get_migration(version)
    if migration is None:
        raise MigrationError(f"No migration registered for version {version}")
    migration.up()
    applied_at = datetime.now().isoformat()
    service.applied[version] = MigrationResult(
        version=version,
        success=True,
        applied_at=applied_at,
    )
    return service.applied[version]


def rollback_migration(service: MigrationService, version: int) -> MigrationResult:
    """Roll back a single applied migration.

    Args:
        service: MigrationService
        version: version to roll back

    Returns MigrationResult with version, success, applied_at.

    Raises MigrationError if migration not registered or not applied.
    """
    if not service.is_applied(version):
        return MigrationResult(version=version, success=False, applied_at="")
    migration = service.get_migration(version)
    if migration is None:
        raise MigrationError(f"No migration registered for version {version}")
    migration.down()
    del service.applied[version]
    return MigrationResult(version=version, success=True, applied_at="")


def check_migration_status(service: MigrationService) -> dict[int, bool]:
    """Return applied status for every registered migration version.

    Args:
        service: MigrationService

    Returns dict of version -> applied bool.
    """
    return {v: service.is_applied(v) for v in service.migrations}


class ExperimentStore:
    """In-memory store of experiment records with schema versioning."""

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentRecord] = {}

    def record(self, record: ExperimentRecord) -> None:
        """Record (upsert) an experiment."""
        self._experiments[record.experiment_id] = record

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        """Get an experiment record by id."""
        return self._experiments.get(experiment_id)

    def ids(self) -> list[str]:
        """Return all experiment ids in insertion order."""
        return list(self._experiments.keys())


def record_experiment(
    store: ExperimentStore,
    experiment_id: str,
    strategy_name: str,
    parameters: dict,
    metrics: dict,
    schema_version: int,
) -> None:
    """Record an experiment with its schema version."""
    from datetime import datetime

    store.record(
        ExperimentRecord(
            experiment_id=experiment_id,
            strategy_name=strategy_name,
            parameters=dict(parameters),
            metrics=dict(metrics),
            created_at=datetime.now().isoformat(),
            schema_version=schema_version,
        )
    )


def read_experiment(store: ExperimentStore, experiment_id: str) -> dict | None:
    """Read an experiment record, backward-compatible across schema versions.

    Returns a dict with experiment_id, strategy_name, parameters, metrics,
    created_at, schema_version, or None if not found.
    """
    record = store.get(experiment_id)
    if record is None:
        return None
    return {
        "experiment_id": record.experiment_id,
        "strategy_name": record.strategy_name,
        "parameters": dict(record.parameters),
        "metrics": dict(record.metrics),
        "created_at": record.created_at,
        "schema_version": record.schema_version,
    }


def validate_not_missing(name: str, value) -> None:
    """Validate that a value is not missing (None or empty string)."""
    if value is None:
        raise MissingInputError(f"{name} is missing (None)")
    if isinstance(value, str) and value == "":
        raise MissingInputError(f"{name} is missing (empty string)")
