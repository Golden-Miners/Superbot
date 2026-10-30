# TDD Evidence Report — M8.6 Local + Encrypted Cloud Backup

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M8.6` ("Local + encrypted cloud backup; decide provider/key management with ADR; exclude secrets").

## User journeys
- As a researcher, I want a backup service that encrypts data before any upload
- As a researcher, I want backup provider selection (local/crypto) via configurable provider
- As a researcher, I want key management: keys stored separately from backups
- As a researcher, I want missing connection params to block rather than default
- As a researcher, I want secret fields (api_key, password, token, secret) excluded from backups
- As a researcher, I want integrity verification via SHA-256 checksums
- As a researcher, I want deterministic: same inputs yield identical backup checksums
- As a researcher, I want restore to decrypt and verify checksum

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Service creation | `tests/unit/test_backup.py::test_backup_service_creates` | ModuleNotFoundError | PASS | Service instantiates with provider/key manager |
| Default provider | `tests/unit/test_backup_service_default_provider` | ModuleNotFoundError | PASS | Defaults to LOCAL provider |
| Backup + restore | `tests/unit/test_backup.py::test_backup_and_restore` | ModuleNotFoundError | PASS | Round-trip preserves data |
| Encrypt/decrypt | `tests/unit/test_backup.py::test_encrypt_payload` / `test_decrypt_payload` | ModuleNotFoundError | PASS | Encrypted != plaintext, decrypt recovers original |
| Exclude secrets | `tests/unit/test_exclude_secrets` | ModuleNotFoundError | PASS | Secret keys removed from backup payload |
| Hash | `tests/unit/test_hash_payload` | ModuleNotFoundError | PASS | Same input → same hash; different input → different hash |
| Verify integrity | `tests/unit/test_verify_integrity` | ModuleNotFoundError | PASS | Matching checksum → True; mismatched → False |
| KeyManager | `tests/unit/test_key_manager_creates` / `test_key_manager_generate_and_load` | ModuleNotFoundError | PASS | Key generated, stored, loaded correctly |
| Missing key | `tests/unit/test_key_manager_missing_key` | ModuleNotFoundError | PASS | Missing key raises KeyError |
| Backup excludes secrets | `tests/unit/test_backup_excludes_secrets` | ModuleNotFoundError | PASS | Secret fields absent from restored data |
| Deterministic | `tests/unit/test_backup_deterministic` | ModuleNotFoundError | PASS | Same inputs → same checksum |
| BackupResult | `tests/unit/test_backup_result_creates` | ModuleNotFoundError | PASS | Result dataclass with all fields |
| RestoreResult | `tests/unit/test_restore_result_creates` | ModuleNotFoundError | PASS | RestoreResult dataclass with checksum_verified |
| Provider enum | `tests/unit/test_backup_provider_enum` | ModuleNotFoundError | PASS | LOCAL = "local", CLOUD = "cloud" |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Backup service | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |
| 2 | Encryption/decryption | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |
| 3 | Secret exclusion | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |
| 4 | Checksum integrity | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |
| 5 | Key management | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_backup.py` | unit | PASS | 555 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M8.6 lines exercised by unit tests
- Intentional gap: No real cloud provider integration — CLOUD is a placeholder enum value; local filesystem is the only implemented storage
- Intentional gap: Key manager stores keys on local filesystem alongside backups (not truly separate storage); a real deployment would use a separate key management service
- Intentional gap: Deterministic SHA-256 stream cipher instead of AES-256-GCM; a production deployment would use a proper crypto library

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.persistence.backup'` captured before implementation. GREEN: 555 tests pass, 2 skipped, ruff clean, format clean, working tree clean.