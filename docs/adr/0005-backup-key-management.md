# ADR-005: Backup key management and authenticated encryption

**Status:** Accepted
**Date:** Sat Oct 31 2026
**Scope:** M12 — Release hardening and migration / Phase 3 backup security

## Decision

Use the `cryptography` package's `Fernet` (AES-128-CBC + HMAC-SHA256) as the
authenticated-encryption implementation for backups. Keys are generated with
`Fernet.generate_key()` (secure random via `os.urandom`) and stored as files in
a key directory separate from backup data. Cloud backup is explicitly
unavailable until its provider and key-management design are implemented.

## Context

The legacy backup implementation used a custom SHA-256 stream cipher
(`encrypt_payload`/`decrypt_payload` in `src/superbot/persistence/backup.py`).
A custom stream cipher is not authenticated encryption: it provides
confidentiality without integrity, is vulnerable to tampering, and is not a
maintained implementation. This ADR replaces it with a maintained,
audited cryptography library.

## Decision

| Requirement | Selection | Rationale |
|-------------|-----------|-----------|
| Authenticated encryption | `cryptography.fernet.Fernet` | Maintained PyPI package (cryptography 50.0.2), AES-128-CBC + HMAC-SHA256, provides confidentiality + integrity + authenticity. Rejects tampered ciphertext via `InvalidToken`. |
| Key generation | `Fernet.generate_key()` | Uses `os.urandom` for secure randomness; produces URL-safe base64-encoded 32-byte keys. |
| Key storage | Files in key directory, separate from backup data | Keys are stored as `{key_name}.key` files; backup data is stored separately as `{backup_id}.json`. Compromise of one does not compromise the other. |
| Key naming | `backup_{experiment_id}.key` | Deterministic mapping from experiment to key, enabling restore. |
| Cloud backup | Unavailable (`NotImplementedError`) | No provider or cloud key-management design exists yet. Explicitly rejected until ADR-defined. |
| Legacy cipher | Disabled (`EncryptionUnavailableError`) | `encrypt_payload`/`decrypt_payload` raise when called; callers must use `BackupService`. |

## Rationale

- **Authenticated encryption:** Fernet combines encryption (AES-128-CBC) with
  authentication (HMAC-SHA256). Any tampering with ciphertext causes
  `InvalidToken` on decrypt, satisfying the tampered-backup rejection
  requirement.
- **Secure random key generation:** `Fernet.generate_key()` calls `os.urandom`,
  which is cryptographically secure on all supported platforms (including
  Windows). This replaces the legacy `sha256(f"{key_name}:{time_ns()}")` which
  was deterministic and predictable.
- **Key separation:** Keys live in a key directory (`keys/` under backup dir by
  default), separate from backup data. This matches the principle that key
  material should not be stored alongside the data it protects.
- **Local-only:** Cloud backup is unavailable by design. The `BackupProvider`
  enum retains `CLOUD` but `BackupService` and `register_provider` raise
  `NotImplementedError` when `CLOUD` is used, until a provider and
  key-management design are implemented.

## Alternatives considered

- **Legacy SHA-256 stream cipher (rejected):** Custom stream cipher provides
  confidentiality without integrity, is vulnerable to bit-flipping and
  replay/tampering attacks, and is not maintained or audited.
- **`cryptography.hazmat` AES-GCM directly (rejected):** Correct but requires
  manual nonce management, associated data, and key derivation. Fernet wraps
  this correctly with built-in nonce handling and key rotation support.
- **`cryptography.hazmat` AES-CTP + HMAC (rejected):** Equivalent security to
  Fernet but more implementation surface; Fernet is the recommended high-level
  API.
- **Cloud backup (deferred):** No cloud provider selected; no key-management
  design for cloud (KMS, HSM, secret store). Explicitly deferred to a future
  ADR.

## Consequences

- `src/superbot/persistence/backup.py` now imports `cryptography.fernet.Fernet`
  as a runtime dependency (declared in `pyproject.toml`).
- `encrypt_payload`/`decrypt_payload` raise `EncryptionUnavailableError`;
  all backup/restore goes through `BackupService`.
- Backup files are persisted to disk as `{backup_id}.json` containing
  experiment_id, checksum, base64-encoded ciphertext, provider, and timestamp.
  Restore reads from disk, so backups survive process restart.
- `KeyManager.generate_key()` now returns `Fernet.generate_key()` bytes
  (secure random), replacing the deterministic `sha256(key_name + time_ns())`.
- Cloud backup raises `NotImplementedError`; no cloud provider or key
  management is implemented.
- The legacy `time_ns`-based key derivation is removed.

## Related

- ADR-002: OHLCV storage format (Parquet selected)
- `src/superbot/persistence/backup.py`: implementation
- `tests/unit/test_backup.py`: tests for authenticated encryption, tamper
  rejection, wrong-key rejection, process restart, cloud unavailability
