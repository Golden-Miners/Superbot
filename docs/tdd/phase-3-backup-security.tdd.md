# TDD Evidence Report — Phase 3: Backup security

**Task:** V1 Stabilization and Security Repair Sprint — Phase 3
**Branch:** `repair/v1-stabilization`
**Date:** Sat Oct 31 2026

---

## Source plan

Evaluation report: `docs/EVALUATION-REPORT-V1-STABILIZATION.md`
- D-5: Custom SHA-256 stream cipher in `src/superbot/persistence/backup.py`
- ADR-005: Backup key management and authenticated encryption (created)

## User journeys

- As a system operator, I want backups encrypted with authenticated encryption
  (Fernet), so tampered ciphertext is detected and rejected
- As a system operator, I want keys generated with secure randomness, so keys
  cannot be predicted or reproduced
- As a system operator, I want keys stored separately from backup data, so
  compromise of one does not compromise the other
- As a system operator, I want tampered backups to be rejected on restore, so
  corrupted data is never silently restored
- As a system operator, I want wrong-key restore attempts to be rejected, so
  only the correct key can decrypt
- As a system operator, I want backups to survive process restart, so restore
  works after a new process starts with the same key directory
- As a system operator, I want cloud backup to be explicitly unavailable, so
  no data is accidentally sent to an unvetted cloud provider
- As a system operator, I want broker credentials excluded from backup
  payloads, so secrets never leak into backups
- As a system operator, I want key-management requirements documented in an
  ADR, so the decision is auditable

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Custom cipher disabled | `tests/unit/test_backup.py::test_encrypt_payload_raises_encryption_unavailable` | ImportError | PASS | `encrypt_payload` raises `EncryptionUnavailableError` |
| Custom cipher disabled | `tests/unit/test_backup.py::test_decrypt_payload_raises_encryption_unavailable` | ImportError | PASS | `decrypt_payload` raises `EncryptionUnavailableError` |
| Secure random key generation | `tests/unit/test_backup.py::test_key_manager_generate_key_is_fernet_key` | ImportError | PASS | `Fernet.generate_key()` used; key validates as Fernet key |
| Keys are unique | `tests/unit/test_backup.py::test_key_manager_generate_keys_are_unique` | ImportError | PASS | 10 calls → 10 distinct keys |
| Key generate + load | `tests/unit/test_backup.py::test_key_manager_generate_and_load` | ImportError | PASS | Generated key loads back identically |
| Missing key → KeyError | `tests/unit/test_backup.py::test_key_manager_missing_key` | ImportError | PASS | Unknown key name raises KeyError |
| Backup + restore | `tests/unit/test_backup.py::test_backup_and_restore_returns_original_data` | ImportError | PASS | Round-trip preserves data; checksum verified |
| Broker credentials excluded | `tests/unit/test_backup.py::test_backup_excludes_broker_credentials` | ImportError | PASS | api_key/password/token not in restored data |
| Tampered backup rejected | `tests/unit/test_backup.py::test_tampered_backup_is_rejected` | ImportError | PASS | Modified ciphertext → `InvalidToken` |
| Wrong key rejected | `tests/unit/test_backup.py::test_wrong_key_is_rejected` | ImportError | PASS | Different key → `InvalidToken` |
| Process restart restore | `tests/unit/test_backup.py::test_process_restart_can_restore` | ImportError | PASS | New BackupService instance + same key dir → restore works |
| Checksum verification | `tests/unit/test_backup.py::test_checksum_mismatch_is_detected` | ImportError | PASS | SHA-256 mismatch detected |
| Cloud unavailable | `tests/unit/test_backup.py::test_cloud_provider_unavailable` | ImportError | PASS | `BackupProvider.CLOUD` → `NotImplementedError` |
| Secret exclusion | `tests/unit/test_backup.py::test_exclude_secrets_removes_broker_credentials` | ImportError | PASS | Secret keys removed from payload |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Custom SHA-256 stream cipher disabled | `tests/unit/test_backup.py::test_encrypt_payload_raises_*` | unit | PASS | 2 tests pass |
| 2 | Fernet authenticated encryption | `tests/unit/test_backup.py::test_backup_and_restore_returns_original_data` | unit | PASS | Round-trip preserves data |
| 3 | Secure random key generation | `tests/unit/test_backup.py::test_key_manager_generate_key_is_fernet_key` | unit | PASS | `Fernet.generate_key()` used |
| 4 | Key uniqueness | `tests/unit/test_backup.py::test_key_manager_generate_keys_are_unique` | unit | PASS | 10 unique keys |
| 5 | Tampered backup rejected | `tests/unit/test_backup.py::test_tampered_backup_is_rejected` | unit | PASS | `InvalidToken` on tamper |
| 6 | Wrong key rejected | `tests/unit/test_backup.py::test_wrong_key_is_rejected` | unit | PASS | `InvalidToken` on wrong key |
| 7 | Process restart restore | `tests/unit/test_backup.py::test_process_restart_can_restore` | unit | PASS | New instance + same key dir restores |
| 8 | Cloud backup unavailable | `tests/unit/test_backup.py::test_cloud_provider_unavailable` | unit | PASS | `NotImplementedError` for CLOUD |
| 9 | Broker credentials excluded | `tests/unit/test_backup.py::test_backup_excludes_broker_credentials` | unit | PASS | No api_key/password/token in restore |
| 10 | Integrity verification | `tests/unit/test_backup.py::test_checksum_mismatch_is_detected` | unit | PASS | SHA-256 checksum verified |

## Coverage and known gaps

- All `superbot.persistence.backup` lines exercised by unit tests (Fernet encrypt/decrypt, key generation/loading, backup/restore, tamper/wrong-key rejection, cloud unavailability, secret exclusion, checksum verification).
- Full `tests/unit` + `tests/e2e` suite exits 0 (MT5-dependent tests skipped without live terminal).
- ruff clean on all new/changed files.
- ADR-005 documents key-management requirements and authenticated-encryption selection.
- `encrypt_payload`/`decrypt_payload` raise `EncryptionUnavailableError`; all callers must use `BackupService`.
- `BackupProvider.CLOUD` raises `NotImplementedError` in `backup()` and `register_provider()`.
- Backups persist to disk as `{backup_id}.json` for process-restart durability.
- Known gap: key rotation / multiple key versions not implemented (single key per experiment_id, overwritten on each backup).
- Known gap: key directory path is configurable but not yet integrated with a broader key-management system (deferred to cloud backup ADR).

## Merge evidence

RED: `ImportError: cannot import name 'EncryptionUnavailableError'` and subsequent auth/API failures captured before implementation. GREEN: 22 Phase 3 tests pass; full `tests/unit` + `tests/e2e` suite exits 0; ruff clean. New/changed files: `src/superbot/persistence/backup.py`, `tests/unit/test_backup.py`, `docs/adr/0005-backup-key-management.md`, `docs/tdd/phase-3-backup-security.tdd.md`.
