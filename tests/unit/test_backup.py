"""RED tests for M8.6 — Local + encrypted cloud backup; disclose missing costs.

Tests define:
- BackupService: encrypts data locally before "upload"
- BackupProvider: abstract provider interface (local + optional cloud)
- Encryption: AES-256-GCM with key derived from passphrase
- Key management: key stored separately from backups; ADR documents provider/key choice
- Secret exclusion: secrets never included in backups
- Backup integrity: SHA-256 checksums for each backup
- Restore: decrypt and verify checksum
- Stdlib-only, no import-time network/cloud activity
"""

from __future__ import annotations

import pytest

from superbot.persistence.backup import (
    BackupProvider,
    BackupResult,
    BackupService,
    KeyManager,
    RestoreResult,
    backup,
    decrypt_payload,
    encrypt_payload,
    exclude_secrets,
    hash_payload,
    verify_integrity,
)


def test_backup_service_creates():
    """BackupService can be created with provider and key manager."""
    service = BackupService(
        provider=BackupProvider.LOCAL,
        backup_dir="/tmp/backup_test",
        key_manager=None,
    )
    assert service is not None


def test_backup_service_default_provider():
    """BackupService defaults to LOCAL provider."""
    service = BackupService(backup_dir="/tmp/backup_test")
    assert service.provider == BackupProvider.LOCAL


def test_backup_and_restore():
    """backup() then restore() returns original data."""
    service = BackupService(backup_dir="/tmp/backup_test")
    service.register_provider(BackupProvider.LOCAL, "/tmp/backup_test_store")
    result = backup(service, "exp_1", {"data": "sensitive"})
    assert result.backup_id is not None
    assert result.checksum is not None
    restored = service.restore(result.backup_id)
    assert restored.restored_data == {"data": "sensitive"}


def test_encrypt_payload():
    """encrypt_payload() returns encrypted bytes."""
    key = b"0123456789abcdef0123456789abcdef"
    encrypted = encrypt_payload(b"secret data", key)
    assert isinstance(encrypted, bytes)
    assert encrypted != b"secret data"


def test_decrypt_payload():
    """decrypt_payload() decrypts encrypted bytes back to original."""
    key = b"0123456789abcdef0123456789abcdef"
    encrypted = encrypt_payload(b"secret data", key)
    decrypted = decrypt_payload(encrypted, key)
    assert decrypted == b"secret data"


def test_exclude_secrets():
    """exclude_secrets() removes secret keys from payload."""
    payload = {
        "data": "visible",
        "api_key": "secret123",
        "password": "hunter2",
        "token": "tok123",
        "normal": "value",
    }
    result = exclude_secrets(payload)
    assert result["data"] == "visible"
    assert result["normal"] == "value"
    assert "api_key" not in result
    assert "password" not in result
    assert "token" not in result


def test_hash_payload():
    """hash_payload() returns SHA-256 hex digest."""
    h1 = hash_payload(b"data")
    h2 = hash_payload(b"data")
    h3 = hash_payload(b"different")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_verify_integrity():
    """verify_integrity() returns True when checksum matches."""
    payload = b"test data"
    h = hash_payload(payload)
    assert verify_integrity(payload, h) is True
    assert verify_integrity(b"wrong", h) is False


def test_key_manager_creates():
    """KeyManager can be created."""
    km = KeyManager(key_dir="/tmp/keymgr_test")
    assert km is not None


def test_key_manager_generate_and_load():
    """KeyManager generates and loads a key."""
    km = KeyManager(key_dir="/tmp/keymgr_test")
    key = km.generate_key("test_key")
    assert len(key) == 32
    loaded = km.load_key("test_key")
    assert loaded == key


def test_key_manager_missing_key():
    """KeyManager.load_key() raises KeyError for missing key."""
    km = KeyManager(key_dir="/tmp/keymgr_test")
    with pytest.raises(KeyError):
        km.load_key("nonexistent")


def test_backup_excludes_secrets():
    """backup() excludes secrets from stored payload."""
    service = BackupService(backup_dir="/tmp/backup_test")
    service.register_provider(BackupProvider.LOCAL, "/tmp/backup_test_store2")
    result = backup(
        service,
        "exp_secret",
        {"data": "visible", "api_key": "secret123", "password": "hunter2"},
    )
    restored = service.restore(result.backup_id)
    assert restored.restored_data["data"] == "visible"
    assert "api_key" not in restored.restored_data
    assert "password" not in restored.restored_data


def test_backup_deterministic():
    """Same inputs yield identical backup checksum."""
    s1 = BackupService(backup_dir="/tmp/backup_test")
    s2 = BackupService(backup_dir="/tmp/backup_test")
    s1.register_provider(BackupProvider.LOCAL, "/tmp/backup_test_store3")
    s2.register_provider(BackupProvider.LOCAL, "/tmp/backup_test_store4")
    r1 = backup(s1, "exp_det", {"data": "same"})
    r2 = backup(s2, "exp_det", {"data": "same"})
    assert r1.checksum == r2.checksum


def test_backup_result_creates():
    """BackupResult can be created."""
    br = BackupResult(
        backup_id="bk_1",
        experiment_id="exp_1",
        checksum="abc123",
        encrypted_size=100,
        provider="local",
    )
    assert br.backup_id == "bk_1"
    assert br.experiment_id == "exp_1"
    assert br.checksum == "abc123"


def test_restore_result_creates():
    """RestoreResult can be created."""
    rr = RestoreResult(
        backup_id="bk_1",
        experiment_id="exp_1",
        restored_data={"data": "visible"},
        checksum_verified=True,
    )
    assert rr.backup_id == "bk_1"
    assert rr.checksum_verified is True


def test_backup_provider_enum():
    """BackupProvider enum has LOCAL and CLOUD values."""
    assert BackupProvider.LOCAL.value == "local"
    assert BackupProvider.CLOUD.value == "cloud"
