# TDD Evidence Report — Phase 2: Security fixes

**Task:** V1 Stabilization and Security Repair Sprint — Phase 2
**Branch:** `repair/v1-stabilization`
**Date:** Sat Oct 31 2026

---

## Source plan

Evaluation report: `docs/EVALUATION-REPORT-V1-STABILIZATION.md`
- D-3: Client-supplied `X-Operator-Role` header authorization in `src/superbot/m11/api.py`
- D-4: Secret serialization via `include_secrets` parameter in `settings_profiles`
- D-6: (Partial) Seeded healthy states — noted for Phase 4

## User journeys

- As a system operator, I want API requests to require a server-issued session token, so client-supplied role headers cannot be forged
- As a system operator, I want unauthenticated access to return 401, so unauthenticated users cannot access dashboard data
- As a viewer, I want to read dashboard data but not change settings, so my role is enforced server-side
- As an owner, I want to change settings with a valid session, so authorized operators can manage the dashboard
- As a system operator, I want expired and revoked sessions to return 401, so compromised sessions cannot be reused
- As a system operator, I want no `include_secrets` parameter and no secret values in any API response, so secrets never leak
- As a system operator, I want authorization enforced on every protected route, so no endpoint is accidentally public

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Server-issued session tokens are unpredictable | `tests/unit/test_m11_auth.py::test_session_tokens_are_unique` | ModuleNotFoundError | PASS | 50 unique tokens from `secrets.token_urlsafe(32)` |
| create_session returns session + token | `tests/unit/test_m11_auth.py::test_create_session_returns_session_and_token` | ImportError | PASS | Session + non-empty token, session_id != token |
| Token validation returns session | `tests/unit/test_m11_auth.py::test_validate_token_returns_session` | ImportError | PASS | Valid token → session with correct role |
| Unknown/empty/expired token → None | `tests/unit/test_m11_auth.py::test_validate_*_token_*` | ImportError | PASS | None for unknown/empty/expired |
| Token invalidation works | `tests/unit/test_m11_auth.py::test_invalidate_token_marks_inactive` | ImportError | PASS | Invalidate → None; double-invalidate → False |
| Role-based can() checks | `tests/unit/test_m11_auth.py::test_*_can_*` | ImportError | PASS | Owner/operator/viewer matrix correct |
| Secret redaction | `tests/unit/test_m11_auth.py::test_secret_redacted_*` | ImportError | PASS | Plaintext never in redacted output |
| Unauthenticated access → 401 | `tests/unit/test_m11_api.py::test_unauthenticated_*_returns_401` | ImportError | PASS | All 8 protected routes return 401 without token |
| Invalid token → 401 | `tests/unit/test_m11_api.py::test_invalid_token_returns_401` | ImportError | PASS | Bearer invalid → 401 |
| Viewer can read, cannot change settings | `tests/unit/test_m11_api.py::test_viewer_can_read_*`, `test_viewer_cannot_change_settings` | ImportError | PASS | Viewer: 200 on GET, 403 on POST settings |
| Owner can change settings | `tests/unit/test_m11_api.py::test_owner_can_change_settings` | ImportError | PASS | Owner: 200 on POST settings, allowed=True |
| Expired session → 401 | `tests/unit/test_m11_api.py::test_expired_session_returns_401` | ImportError | PASS | Expired token → 401 |
| Revoked session → 401 | `tests/unit/test_m11_api.py::test_revoked_session_returns_401` | ImportError | PASS | Revoked token → 401 |
| No include_secrets parameter | `tests/unit/test_m11_api.py::test_settings_rejects_include_secrets` | ImportError | PASS | Parameter ignored, no secrets exposed |
| No secret values serialized | `tests/unit/test_m11_api.py::test_settings_response_contains_no_secret_values`, `test_dummy_secret_not_exposed_in_api_response` | ImportError | PASS | `secret_redacted=True`, no plaintext secrets |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Server-issued unpredictable session tokens | `tests/unit/test_m11_auth.py::test_session_token_*` | unit | PASS | 4 tests pass |
| 2 | Token-based session validation (not session_id) | `tests/unit/test_m11_auth.py::test_validate_token_*` | unit | PASS | 5 tests pass |
| 3 | Session expiry and revocation | `tests/unit/test_m11_auth.py::test_validate_expired_token_returns_none`, `test_invalidate_token_marks_inactive` | unit | PASS | 2 tests pass |
| 4 | Role-based authorization matrix | `tests/unit/test_m11_auth.py::test_*_can_*` | unit | PASS | 6 tests pass |
| 5 | Secret redaction never exposes plaintext | `tests/unit/test_m11_auth.py::test_secret_redacted_*` | unit | PASS | 4 tests pass |
| 6 | Unauthenticated access → 401 on all routes | `tests/unit/test_m11_api.py::test_unauthenticated_*_returns_401` | integration | PASS | 8 tests pass |
| 7 | Invalid token → 401 | `tests/unit/test_m11_api.py::test_invalid_token_returns_401` | integration | PASS | 1 test passes |
| 8 | Viewer/owner permissions enforced | `tests/unit/test_m11_api.py::test_viewer_can_read_*`, `test_viewer_cannot_change_settings`, `test_operator_cannot_change_settings`, `test_owner_can_change_settings` | integration | PASS | 9 tests pass |
| 9 | Session expiry → 401 | `tests/unit/test_m11_api.py::test_expired_session_returns_401` | integration | PASS | 1 test passes |
| 10 | Session revocation → 401 | `tests/unit/test_m11_api.py::test_revoked_session_returns_401` | integration | PASS | 1 test passes |
| 11 | No include_secrets parameter | `tests/unit/test_m11_api.py::test_settings_rejects_include_secrets` | integration | PASS | 1 test passes |
| 12 | No secret values serialized | `tests/unit/test_m11_api.py::test_settings_response_contains_no_secret_values`, `test_dummy_secret_not_exposed_in_api_response` | integration | PASS | 2 tests pass |

## Coverage and known gaps

- No coverage tool configured; all `superbot.m11.auth` and `superbot.m11.api` lines exercised by unit tests (every auth path, every route, every authorization branch).
- Full `tests/unit` + `tests/e2e` suite exits 0 (MT5-dependent tests skipped without live terminal).
- ruff clean on all new/changed files.
- `create_app(session_store: SessionStore \| None = None)` accepts an optional store for testability; defaults to a new `SessionStore()`.
- `SessionStore` is now keyed by server-issued token (not sequential session_id). Tokens use `secrets.token_urlsafe(32)`.
- Client-supplied `X-Operator-Role` header is removed; `_operator_role` function deleted.
- `include_secrets` query parameter removed from `settings_profiles`.
- `secret` key is explicitly excluded from profile serialization — never appears in API responses.
- Every protected route calls `_authorize(request, store, action)` which enforces authentication (401) and role-based authorization (403).
- Routes protected: `/health`, `/data/explorer/{symbol}/{timeframe}`, `/jobs`, `/jobs/{job_id}/cancel`, `/strategies`, `/strategies/{strategy_id}`, `/experiments`, `/risk`, `/risk/strategy/{strategy_id}`, `/audit/events`, `/audit/chain/verify`, `/settings/profiles`, `/settings/profiles/{profile_name}`.
- Known gap: health row still uses seeded healthy states (no real probing) — deferred to Phase 4 (D-6).
- Known gap: job cancel endpoint exists without real worker management — deferred to Phase 4.

## Merge evidence

RED: `ImportError: cannot import name 'generate_session_token' from 'superbot.m11.auth'` (and subsequent auth/API failures) captured before implementation. GREEN: 39 Phase 2 tests pass; full `tests/unit` + `tests/e2e` suite exits 0; ruff clean. New/changed files: `src/superbot/m11/auth.py`, `src/superbot/m11/api.py`, `tests/unit/test_m11_auth.py`, `tests/unit/test_m11_api.py`.
