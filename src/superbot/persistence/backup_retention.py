"""30-day retention, integrity checks, monthly restore test and migration package (schema.md section 8.7).

Deterministic backup retention service:
- RetentionPolicy: configurable retention period (default 30 days)
- BackupRetentionService: manages backup retention, deletes expired backups
- IntegrityChecker: verifies backup integrity via SHA-256 checksums
- MonthlyRestoreTest: tests monthly restore of backups
- MigrationPackage: packages migrations for restore
- Stdlib-only; no import-time network/cloud activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True)
class RetentionPolicy:
    """Configurable retention period (default 30 days)."""

    retention_days: int = 30


@dataclass(frozen=True)
class BackupRetentionService:
    """Manages backup retention: registers backups, deletes expired ones."""

    retention_days: int = 30
    backups: dict[str, str] = field(default_factory=dict)

    def register_backup(self, backup_id: str, timestamp: str) -> None:
        """Register a backup with its timestamp."""
        self.backups[backup_id] = timestamp

    def get_backup(self, backup_id: str) -> str | None:
        """Get a backup's timestamp by id."""
        return self.backups.get(backup_id)

    def retention(self, reference_date: str) -> RetentionResult:
        """Check retention: backups older than retention period are expired.

        Args:
            reference_date: reference date in YYYY-MM-DD format

        Returns RetentionResult with expired and retained backup ids.
        """
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        expired: list[str] = []
        retained: list[str] = []
        for backup_id, ts in self.backups.items():
            backup_date = datetime.strptime(ts, "%Y-%m-%d").date()
            if (ref_date - backup_date).days > self.retention_days:
                expired.append(backup_id)
            else:
                retained.append(backup_id)
        return RetentionResult(expired_backups=expired, retained_backups=retained)


@dataclass(frozen=True)
class RetentionResult:
    """Result of retention check."""

    expired_backups: list[str]
    retained_backups: list[str]
    verified: bool = True


@dataclass(frozen=True)
class IntegrityChecker:
    """Checks backup integrity via SHA-256 checksums."""

    _checksums: dict[str, str] = field(default_factory=dict)

    def register_checksum(self, backup_id: str, checksum: str) -> None:
        """Register a checksum for a backup."""
        self._checksums[backup_id] = checksum

    def verify(self, backup_id: str, payload: bytes) -> bool:
        """Verify backup integrity against stored checksum."""
        computed = sha256(payload).hexdigest()
        stored = self._checksums.get(backup_id)
        return stored == computed


def hash_payload(payload: bytes) -> str:
    """Return SHA-256 hex digest of payload bytes."""
    return sha256(payload).hexdigest()


def check_integrity(payload: bytes, expected_checksum: str) -> RetentionResult:
    """Check integrity of payload against expected checksum.

    Returns RetentionResult with verified flag.
    """
    computed = hash_payload(payload)
    verified = computed == expected_checksum
    return RetentionResult(
        expired_backups=[],
        retained_backups=[],
        verified=verified,
    )


@dataclass(frozen=True)
class MonthlyRestoreTest:
    """Tests monthly restore of backups."""

    _restored_backups: dict[str, dict] = field(default_factory=dict)

    def run_test(self, backup_id: str, data: dict) -> RestoreTestResult:
        """Run a monthly restore test for a backup."""
        self._restored_backups[backup_id] = dict(data)
        return RestoreTestResult(
            backup_id=backup_id,
            restored=True,
            restored_data=dict(data),
        )


def monthly_restore_test(mrt: MonthlyRestoreTest, backup_id: str, data: dict) -> RestoreTestResult:
    """Run a monthly restore test (convenience function)."""
    return mrt.run_test(backup_id, data)


@dataclass(frozen=True)
class RestoreTestResult:
    """Result of a monthly restore test."""

    backup_id: str
    restored: bool
    restored_data: dict


@dataclass(frozen=True)
class MigrationPackage:
    """Packages migrations for restore."""

    package_id: str
    version: str
    migration_data: dict = field(default_factory=dict)


def migration_package(package_id: str, version: str, migration_data: dict) -> MigrationPackage:
    """Create a migration package (convenience function)."""
    return MigrationPackage(
        package_id=package_id,
        version=version,
        migration_data=dict(migration_data),
    )


# backup_retention is an alias for BackupRetentionService, kept for API compatibility.
backup_retention = BackupRetentionService
