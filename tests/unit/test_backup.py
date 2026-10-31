"""RED tests for Phase 3 — Backup security.

Covers: authenticated encryption (Fernet), secure random key generation,
tampered backup rejection, wrong-key rejection, recovery, process restart,
no broker credentials in backup payloads, cloud backup unavailable.

Acceptance: custom SHA-256 stream cipher disabled for real data;
maintained authenticated-encryption implementation used;
secure random key generation; ADR defines key-management requirements;
durable local backup/restore with integrity verification;
cloud backup explicitly unavailable;
tampered/wrong-key rejection; recovery and restart tested;
no broker credentials in backup payloads.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile

import pytest
from cryptography.fernet import Fernet, InvalidToken

from superbot.persistence.backup import (
    BackupProvider,
    BackupResult,
    BackupService,
    EncryptionUnavailableError,
    KeyManager,
    RestoreResult,
    backup,
    decrypt_payload,
    encrypt_payload,
    exclude_secrets,
    hash_payload,
    verify_integrity,
)


def _make_service() -> BackupService:
    """Create a BackupService with temp backup and key dirs."""
    backup_dir = tempfile.mkdtemp(prefix="backup_test_")
    key_dir = tempfile.mkdtemp(prefix="backup_keys_")
    return BackupService(
        backup_dir=backup_dir,
        provider=BackupProvider.LOCAL,
        key_manager=KeyManager(key_dir),
    )


# --- Custom cipher disabled ----------------------------------------------


def test_encrypt_payload_raises_encryption_unavailable():
    """Custom SHA-256 stream cipher is disabled; encrypt_payload raises."""
    key = Fernet.generate_key()
    with pytest.raises(EncryptionUnavailableError):
        encrypt_payload(b"secret data", key)


def test_decrypt_payload_raises_encryption_unavailable():
    """Custom SHA-256 stream cipher is disabled; decrypt_payload raises."""
    key = Fernet.generate_key()
    with pytest.raises(EncryptionUnavailableError):
        decrypt_payload(b"fake-token-data", key)


# --- Secure random key generation ----------------------------------------

def test_key_manager_generate_key_is_fernet_key():
    """KeyManager.generate_key() returns a valid Fernet key (secure random)."""
    key_dir = tempfile.mkdtemp(prefix="keys_")
    km = KeyManager(key_dir)
    key = km.generate_key("test_key")
    # Fernet keys are URL-safe base64-encoded 32-byte keys; Fernet() validates.
    Fernet(key)  # raises if invalid
    assert len(key) == 44  # base64 of 32 bytes with padding


def test_key_manager_generate_keys_are_unique():
    """Each generate_key call produces a different key."""
    key_dir = tempfile.mkdtemp(prefix="keys_")
    km = KeyManager(key_dir)
    keys = [km.generate_key(f"key_{i}") for i in range(10)]
    assert len(set(keys)) == 10


def test_key_manager_generate_and_load():
    """KeyManager generates and loads a key."""
    key_dir = tempfile.mkdtemp(prefix="keys_")
    km = KeyManager(key_dir)
    key = km.generate_key("test_key")
    loaded = km.load_key("test_key")
    assert loaded == key


def test_key_manager_missing_key():
    """KeyManager.load_key() raises KeyError for missing key."""
    key_dir = tempfile.mkdtemp(prefix="keys_")
    km = KeyManager(key_dir)
    with pytest.raises(KeyError):
        km.load_key("nonexistent")


# --- Backup / restore with authenticated encryption -----------------------

def test_backup_and_restore_returns_original_data():
    """backup() then restore() returns original data via Fernet."""
    service = _make_service()
    result = backup(service, "exp_1", {"data": "sensitive", "value": 42})
    assert isinstance(result, BackupResult)
    assert result.backup_id is not None
    assert result.checksum is not None
    restored = service.restore(result.backup_id)
    assert restored.restored_data == {"data": "sensitive", "value": 42}
    assert restored.checksum_verified is True


def test_backup_excludes_broker_credentials():
    """backup() excludes broker credentials from stored payload."""
    service = _make_service()
    result = backup(
        service,
        "exp_secret",
        {"data": "visible", "api_key": "secret123", "password": "hunter2", "token": "tok123"},
    )
    restored = service.restore(result.backup_id)
    assert restored.restored_data["data"] == "visible"
    assert "api_key" not in restored.restored_data
    assert "password" not in restored.restored_data
    assert "token" not in restored.restored_data


def test_tampered_backup_is_rejected():
    """Tampering with encrypted bytes causes restore to raise InvalidToken."""
    service = _make_service()
    result = backup(service, "exp_tamper", {"data": "sensitive"})
    backup_path = os.path.join(service.backup_dir, f"{result.backup_id}.json")
    with open(backup_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Decode, flip a byte in the raw encrypted bytes, re-encode.
    encrypted = bytearray(base64.b64decode(data["encrypted"]))
    encrypted[0] ^= 0xFF
    data["encrypted"] = base64.b64encode(bytes(encrypted)).decode("ascii")
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    with pytest.raises(InvalidToken):
        service.restore(result.backup_id)


def test_wrong_key_is_rejected():
    """Decrypting with a different key raises InvalidToken."""
    service = _make_service()
    result = backup(service, "exp_wrong", {"data": "sensitive"})
    # Overwrite the key file with a different key.
    wrong_key = Fernet.generate_key()
    key_path = os.path.join(service.key_manager.key_dir, "backup_exp_wrong.key")
    with open(key_path, "wb") as fh:
        fh.write(wrong_key)
    with pytest.raises(InvalidToken):
        service.restore(result.backup_id)


def test_process_restart_can_restore():
    """A new BackupService with the same key dir can restore existing backups."""
    backup_dir = tempfile.mkdtemp(prefix="backup_restart_")
    key_dir = tempfile.mkdtemp(prefix="keys_restart_")
    service1 = BackupService(
        backup_dir=backup_dir,
        provider=BackupProvider.LOCAL,
        key_manager=KeyManager(key_dir),
    )
    result = backup(service1, "exp_restart", {"data": "persist"})

    # New service instance, same key dir (simulates process restart).
    service2 = BackupService(
        backup_dir=backup_dir,
        provider=BackupProvider.LOCAL,
        key_manager=KeyManager(key_dir),
    )
    restored = service2.restore(result.backup_id)
    assert restored.restored_data == {"data": "persist"}
    assert restored.checksum_verified is True


def test_checksum_mismatch_is_detected():
    """verify_integrity detects mismatched checksums."""
    payload = b"test data"
    h = hash_payload(payload)
    assert verify_integrity(payload, h) is True
    assert verify_integrity(b"wrong data", h) is False


# --- Cloud backup unavailable --------------------------------------------

def test_cloud_provider_unavailable():
    """Cloud backup is explicitly unavailable."""
    key_dir = tempfile.mkdtemp(prefix="keys_cloud_")
    service = BackupService(
        backup_dir=tempfile.mkdtemp(prefix="backup_cloud_"),
        provider=BackupProvider.CLOUD,
        key_manager=KeyManager(key_dir),
    )
    with pytest.raises(NotImplementedError):
        backup(service, "exp_cloud", {"data": "sensitive"})


# --- Secret exclusion ----------------------------------------------------

def test_exclude_secrets_removes_broker_credentials():
    """exclude_secrets() removes broker credential keys."""
    payload = {
        "data": "visible",
        "api_key": "sk-live-1234567890",
        "password": "hunter2",
        "token": "abc123",
        "secret": "mysecret",
        "normal": "value",
    }
    result = exclude_secrets(payload)
    assert result["data"] == "visible"
    assert result["normal"] == "value"
    for k in ("api_key", "password", "token", "secret"):
        assert k not in result


# --- Deterministic checksum ----------------------------------------------

def test_hash_payload_is_deterministic():
    """hash_payload() returns SHA-256 hex digest."""
    h1 = hash_payload(b"data")
    h2 = hash_payload(b"data")
    h3 = hash_payload(b"different")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


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
