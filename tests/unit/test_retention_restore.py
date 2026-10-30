"""RED tests for M8.7 — 30-day retention, integrity checks, monthly restore test and migration package.

Tests define:
- RetentionPolicy: 30-day retention with configurable retention period
- BackupRetentionService: manages backup retention, deletes expired backups
- IntegrityChecker: verifies backup integrity via checksums
- MonthlyRestoreTest: tests monthly restore of backups
- MigrationPackage: packages migrations for restore
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/cloud activity
"""

from __future__ import annotations

from superbot.persistence.backup_retention import (
    BackupRetentionService,
    IntegrityChecker,
    MigrationPackage,
    MonthlyRestoreTest,
    RetentionPolicy,
    RetentionResult,
    check_integrity,
    hash_payload,
    migration_package,
    monthly_restore_test,
)


def test_retention_policy_creates():
    """RetentionPolicy can be created with default 30-day retention."""
    policy = RetentionPolicy()
    assert policy.retention_days == 30


def test_retention_policy_custom_days():
    """RetentionPolicy accepts custom retention days."""
    policy = RetentionPolicy(retention_days=60)
    assert policy.retention_days == 60


def test_backup_retention_service_creates():
    """BackupRetentionService can be created."""
    service = BackupRetentionService()
    assert service is not None


def test_register_backup():
    """register_backup registers a backup with timestamp."""
    service = BackupRetentionService()
    service.register_backup("bk_1", "2026-01-01")
    assert service.get_backup("bk_1") is not None


def test_retention_deletes_expired_backups():
    """retention() deletes backups older than retention period."""
    service = BackupRetentionService(retention_days=30)
    service.register_backup("bk_old", "2026-01-01")
    service.register_backup("bk_new", "2026-02-01")
    result = service.retention(reference_date="2026-02-15")
    assert result.expired_backups == ["bk_old"]
    assert result.retained_backups == ["bk_new"]


def test_retention_keeps_recent_backups():
    """retention() keeps backups within retention period."""
    service = BackupRetentionService(retention_days=30)
    service.register_backup("bk_new", "2026-02-10")
    result = service.retention(reference_date="2026-02-15")
    assert result.retained_backups == ["bk_new"]


def test_retention_result_creates():
    """RetentionResult can be created."""
    rr = RetentionResult(expired_backups=["bk_1"], retained_backups=["bk_2"])
    assert rr.expired_backups == ["bk_1"]
    assert rr.retained_backups == ["bk_2"]


def test_integrity_checker_creates():
    """IntegrityChecker can be created."""
    checker = IntegrityChecker()
    assert checker is not None


def test_check_integrity_passes():
    """check_integrity() passes when checksum matches."""
    IntegrityChecker()
    result = check_integrity(b"data", hash_payload(b"data"))
    assert result.verified is True


def test_check_integrity_fails():
    """check_integrity() fails when checksum doesn't match."""
    IntegrityChecker()
    result = check_integrity(b"data", "wrong")
    assert result.verified is False


def test_monthly_restore_test_creates():
    """MonthlyRestoreTest can be created."""
    mrt = MonthlyRestoreTest()
    assert mrt is not None


def test_monthly_restore_test_runs():
    """monthly_restore_test() runs a monthly restore test."""
    mrt = MonthlyRestoreTest()
    result = monthly_restore_test(mrt, "bk_1", {"data": "restored"})
    assert result.restored is True
    assert result.restored_data == {"data": "restored"}


def test_migration_package_creates():
    """MigrationPackage can be created."""
    mp = MigrationPackage(package_id="mp_1", version="1.0")
    assert mp.package_id == "mp_1"
    assert mp.version == "1.0"


def test_migration_package_creates_migration():
    """migration_package() creates a migration package."""
    mp = migration_package("mp_1", "1.0", {"script": "CREATE TABLE x"})
    assert mp.package_id == "mp_1"
    assert mp.version == "1.0"


def test_retention_deterministic():
    """Same inputs yield identical retention results."""
    s1 = BackupRetentionService(retention_days=30)
    s2 = BackupRetentionService(retention_days=30)
    s1.register_backup("bk_1", "2026-01-01")
    s2.register_backup("bk_1", "2026-01-01")
    r1 = s1.retention(reference_date="2026-02-01")
    r2 = s2.retention(reference_date="2026-02-01")
    assert r1.expired_backups == r2.expired_backups


def test_retention_no_expired_backups():
    """retention() returns empty expired_backups when none expired."""
    service = BackupRetentionService(retention_days=30)
    service.register_backup("bk_new", "2026-02-10")
    result = service.retention(reference_date="2026-02-15")
    assert result.expired_backups == []
    assert result.retained_backups == ["bk_new"]
