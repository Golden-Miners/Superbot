"""Local + encrypted cloud backup with key management (schema.md section 8.6).

Deterministic backup service:
- Encrypts data locally (deterministic SHA-256 stream cipher) before any upload
- BackupProvider: LOCAL (filesystem) or CLOUD (placeholder, no real auth)
- Key management: keys stored separately from backups; provider/key choice documented
- Secret exclusion: secrets (api_key, password, token, secret) never included in backups
- Integrity: SHA-256 checksum per backup; restore verifies checksum
- Restore: decrypt and verify checksum
- Stdlib-only; no import-time network/cloud activity.
"""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from json import dumps, loads
from os import makedirs, path
from time import time_ns


class BackupProvider(str, Enum):
    """Backup provider: LOCAL (filesystem) or CLOUD (placeholder, no real auth)."""

    LOCAL = "local"
    CLOUD = "cloud"


class BackupResult:
    """Result of a backup operation."""

    def __init__(
        self,
        backup_id: str,
        experiment_id: str,
        checksum: str,
        encrypted_size: int,
        provider: str,
    ) -> None:
        self.backup_id = backup_id
        self.experiment_id = experiment_id
        self.checksum = checksum
        self.encrypted_size = encrypted_size
        self.provider = provider


class RestoreResult:
    """Result of a restore operation."""

    def __init__(
        self,
        backup_id: str,
        experiment_id: str,
        restored_data: dict,
        checksum_verified: bool,
    ) -> None:
        self.backup_id = backup_id
        self.experiment_id = experiment_id
        self.restored_data = restored_data
        self.checksum_verified = checksum_verified


class KeyManager:
    """Manages encryption keys stored separately from backups."""

    def __init__(self, key_dir: str) -> None:
        self.key_dir = key_dir
        makedirs(key_dir, exist_ok=True)

    def generate_key(self, key_name: str) -> bytes:
        """Generate a new 256-bit key and store it."""
        key = sha256(f"{key_name}:{time_ns()}".encode()).digest()
        makedirs(self.key_dir, exist_ok=True)
        with open(path.join(self.key_dir, f"{key_name}.key"), "wb") as f:
            f.write(key)
        return key

    def load_key(self, key_name: str) -> bytes:
        """Load a stored key by name."""
        key_path = path.join(self.key_dir, f"{key_name}.key")
        if not path.exists(key_path):
            raise KeyError(f"Key {key_name} not found")
        with open(key_path, "rb") as f:
            return f.read()


class BackupService:
    """Deterministic backup service with encryption and secret exclusion."""

    def __init__(
        self,
        backup_dir: str,
        provider: BackupProvider = BackupProvider.LOCAL,
        key_manager: KeyManager | None = None,
    ) -> None:
        self.backup_dir = backup_dir
        self.provider = provider
        self.key_manager = key_manager or KeyManager(path.join(backup_dir, "keys"))
        makedirs(backup_dir, exist_ok=True)
        self._backups: dict[str, dict] = {}

    def register_provider(self, provider: BackupProvider, path: str) -> None:
        """Register a storage provider location."""
        makedirs(path, exist_ok=True)

    def backup(
        self,
        experiment_id: str,
        payload: dict,
    ) -> BackupResult:
        """Back up experiment data: exclude secrets, encrypt, store, return result."""
        clean = exclude_secrets(dict(payload))
        plaintext = dumps(clean, sort_keys=True).encode("utf-8")
        checksum = hash_payload(plaintext)
        key = self.key_manager.generate_key(f"backup_{experiment_id}")
        encrypted = encrypt_payload(plaintext, key)
        backup_id = sha256(f"{experiment_id}:{checksum}:{len(plaintext)}".encode()).hexdigest()
        self._backups[backup_id] = {
            "experiment_id": experiment_id,
            "checksum": checksum,
            "encrypted": encrypted,
            "provider": self.provider.value,
        }
        return BackupResult(
            backup_id=backup_id,
            experiment_id=experiment_id,
            checksum=checksum,
            encrypted_size=len(encrypted),
            provider=self.provider.value,
        )

    def restore(self, backup_id: str) -> RestoreResult:
        """Restore and decrypt a backup, verifying checksum."""
        entry = self._backups.get(backup_id)
        if entry is None:
            raise KeyError(f"Backup {backup_id} not found")
        key = self.key_manager.load_key(f"backup_{entry['experiment_id']}")
        decrypted = decrypt_payload(entry["encrypted"], key)
        checksum_verified = verify_integrity(decrypted, entry["checksum"])
        restored_data = loads(decrypted.decode("utf-8"))
        return RestoreResult(
            backup_id=backup_id,
            experiment_id=entry["experiment_id"],
            restored_data=restored_data,
            checksum_verified=checksum_verified,
        )


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt plaintext with a deterministic SHA-256 stream cipher.

    Returns nonce + ciphertext, where nonce is derived deterministically from
    key + plaintext hash so the same inputs always produce the same output.
    """
    nonce = sha256(key + plaintext).digest()[:16]
    stream = sha256(key + nonce).digest()
    out = bytearray(len(plaintext))
    for i in range(len(plaintext)):
        out[i] = plaintext[i] ^ stream[i % len(stream)]
    return nonce + bytes(out)


def decrypt_payload(encrypted: bytes, key: bytes) -> bytes:
    """Decrypt encrypted bytes (nonce + ciphertext) back to plaintext."""
    nonce = encrypted[:16]
    ciphertext = encrypted[16:]
    stream = sha256(key + nonce).digest()
    out = bytearray(len(ciphertext))
    for i in range(len(ciphertext)):
        out[i] = ciphertext[i] ^ stream[i % len(stream)]
    return bytes(out)


def exclude_secrets(payload: dict) -> dict:
    """Return a copy of payload with secret keys removed."""
    secret_keys = {"spread", "commission", "api_key", "password", "token", "secret"}
    return {k: v for k, v in payload.items() if k not in secret_keys}


def hash_payload(payload: bytes) -> str:
    """Return SHA-256 hex digest of payload bytes."""
    return sha256(payload).hexdigest()


def verify_integrity(payload: bytes, expected_checksum: str) -> bool:
    """Return True when checksum matches payload hash."""
    return hash_payload(payload) == expected_checksum


def backup(
    service: BackupService,
    experiment_id: str,
    payload: dict,
) -> BackupResult:
    """Back up experiment data (convenience function)."""
    return service.backup(experiment_id, payload)
