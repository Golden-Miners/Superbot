"""Local + encrypted backup with authenticated encryption (schema.md section 8.6).

Deterministic backup service:
- Encrypts data locally using Fernet (AES-128-CBC + HMAC-SHA256) from the
  cryptography package — authenticated encryption, never a custom stream cipher.
- BackupProvider: LOCAL (filesystem) only; CLOUD is explicitly unavailable
  until its provider and key-management design are implemented.
- Key management: keys generated with Fernet.generate_key() (secure random via
  os.urandom) and stored separately from backups; key-management requirements
  recorded in ADR-005.
- Secret exclusion: secrets (api_key, password, token, secret) never included
  in backups.
- Integrity: SHA-256 checksum per backup plus Fernet's built-in HMAC;
  restore verifies both.
- Restore: decrypt with Fernet (rejects tampered or wrong-key ciphertext via
  InvalidToken), verify checksum, deserialize.
- No import-time network/cloud activity; cloud backup is not available.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from json import dumps, loads
from os import makedirs, path

from cryptography.fernet import Fernet


class EncryptionUnavailableError(RuntimeError):
    """Raised when the disabled custom stream cipher is used.

    The legacy SHA-256 stream cipher (encrypt_payload/decrypt_payload) is
    disabled for real data. Use BackupService with Fernet-based authenticated
    encryption instead.
    """


class BackupProvider(str, Enum):
    """Backup provider: LOCAL (filesystem) only; CLOUD unavailable."""

    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class BackupResult:
    """Result of a backup operation."""

    backup_id: str
    experiment_id: str
    checksum: str
    encrypted_size: int
    provider: str


@dataclass
class RestoreResult:
    """Result of a restore operation."""

    backup_id: str
    experiment_id: str
    restored_data: dict
    checksum_verified: bool


class KeyManager:
    """Manages encryption keys stored separately from backups.

    Keys are generated with Fernet.generate_key(), which uses os.urandom for
    secure randomness. Keys are stored as files in key_dir, separate from
    backup data.
    """

    def __init__(self, key_dir: str) -> None:
        self.key_dir = key_dir
        makedirs(key_dir, exist_ok=True)

    def generate_key(self, key_name: str) -> bytes:
        """Generate a new Fernet key and store it.

        Returns a URL-safe base64-encoded 32-byte key suitable for Fernet.
        """
        key = Fernet.generate_key()
        makedirs(self.key_dir, exist_ok=True)
        with open(path.join(self.key_dir, f"{key_name}.key"), "wb") as fh:
            fh.write(key)
        return key

    def load_key(self, key_name: str) -> bytes:
        """Load a stored key by name."""
        key_path = path.join(self.key_dir, f"{key_name}.key")
        if not path.exists(key_path):
            raise KeyError(f"Key {key_name} not found")
        with open(key_path, "rb") as fh:
            return fh.read()


class BackupService:
    """Durable local backup service with authenticated encryption.

    Encrypts with Fernet (authenticated encryption: AES-128-CBC + HMAC-SHA256).
    Persists backup metadata and ciphertext to disk so backups survive process
    restart. Cloud backup is explicitly unavailable.
    """

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

    def register_provider(self, provider: BackupProvider, p: str) -> None:
        """Register a storage provider location (LOCAL only)."""
        if provider == BackupProvider.CLOUD:
            raise NotImplementedError(
                "Cloud backup is unavailable until its provider and "
                "key-management design are implemented (ADR-005)."
            )
        makedirs(p, exist_ok=True)

    def backup(
        self,
        experiment_id: str,
        payload: dict,
    ) -> BackupResult:
        """Back up experiment data: exclude secrets, encrypt with Fernet,
        persist to disk, return result.
        """
        if self.provider == BackupProvider.CLOUD:
            raise NotImplementedError(
                "Cloud backup is unavailable until its provider and "
                "key-management design are implemented (ADR-005)."
            )
        clean = exclude_secrets(dict(payload))
        plaintext = dumps(clean, sort_keys=True).encode("utf-8")
        checksum = hash_payload(plaintext)
        # Only generate a new key if one doesn't already exist for this
        # experiment. Reusing the same key ensures older backups remain
        # restorable when the same experiment is backed up again.
        key_name = f"backup_{experiment_id}"
        try:
            key = self.key_manager.load_key(key_name)
        except KeyError:
            key = self.key_manager.generate_key(key_name)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(plaintext)
        backup_id = sha256(
            f"{experiment_id}:{checksum}:{len(plaintext)}".encode()
        ).hexdigest()

        # Persist to disk for durability across process restart.
        backup_data = {
            "experiment_id": experiment_id,
            "checksum": checksum,
            "encrypted": base64.b64encode(encrypted).decode("ascii"),
            "provider": self.provider.value,
            "created_at_utc": datetime.now(tz=UTC).isoformat(),
        }
        backup_path = path.join(self.backup_dir, f"{backup_id}.json")
        with open(backup_path, "w", encoding="utf-8") as fh:
            json.dump(backup_data, fh)

        return BackupResult(
            backup_id=backup_id,
            experiment_id=experiment_id,
            checksum=checksum,
            encrypted_size=len(encrypted),
            provider=self.provider.value,
        )

    def restore(self, backup_id: str) -> RestoreResult:
        """Restore and decrypt a backup, verifying checksum and integrity.

        Raises KeyError if the backup does not exist, Fernet InvalidToken if
        the ciphertext is tampered with or the wrong key is used.
        """
        backup_path = path.join(self.backup_dir, f"{backup_id}.json")
        if not path.exists(backup_path):
            raise KeyError(f"Backup {backup_id} not found")
        with open(backup_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        experiment_id = data["experiment_id"]
        expected_checksum = data["checksum"]
        key = self.key_manager.load_key(f"backup_{experiment_id}")
        fernet = Fernet(key)
        encrypted = base64.b64decode(data["encrypted"])
        # Fernet.decrypt raises InvalidToken on tampering or wrong key.
        decrypted = fernet.decrypt(encrypted)
        checksum_verified = verify_integrity(decrypted, expected_checksum)
        restored_data = loads(decrypted.decode("utf-8"))
        return RestoreResult(
            backup_id=backup_id,
            experiment_id=experiment_id,
            restored_data=restored_data,
            checksum_verified=checksum_verified,
        )


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """Disabled: the custom SHA-256 stream cipher is not available.

    Use BackupService with Fernet-based authenticated encryption instead.
    """
    raise EncryptionUnavailableError(
        "encrypt_payload (custom SHA-256 stream cipher) is disabled. "
        "Use BackupService.backup() which uses Fernet authenticated encryption."
    )


def decrypt_payload(encrypted: bytes, key: bytes) -> bytes:
    """Disabled: the custom SHA-256 stream cipher is not available.

    Use BackupService with Fernet-based authenticated encryption instead.
    """
    raise EncryptionUnavailableError(
        "decrypt_payload (custom SHA-256 stream cipher) is disabled. "
        "Use BackupService.restore() which uses Fernet authenticated encryption."
    )


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
