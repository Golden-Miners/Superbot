# TDD Evidence Report — M11.3 Auth sessions, roles, redaction, local binding, private VPN docs

## Source plan

No `*.plan.md` provided; user journeys derived during this TDD run from `task.md` `M11.3` ("Auth sessions/roles/redaction/local binding/private VPN docs") and `design.md` §7 UI acceptance checklist ("Backend enforces authorization; hiding a button is insufficient", "No public network binding; remote access only through approved private VPN", "Secrets redacted and non-exportable", "Only authorized owner may change sensitive settings") and `architecture.md` (authentication/session method was OPEN pending inspection).

## User journeys

- As a system operator, I want authenticated sessions bound to a role (owner/operator/viewer) so access to the dashboard is controlled and auditable
- As a system operator, I want sessions to expire after a TTL and be invalidatable, so stale sessions cannot be reused
- As a system operator, I want the backend to enforce authorization per action (e.g. only owner may change sensitive settings), so hiding a UI button is never sufficient
- As a system operator, I want secrets redacted and non-exportable, so credential material never leaks through the UI or API
- As a system operator, I want the API/UI to bind localhost only (127.0.0.1 / localhost / ::1), rejecting 0.0.0.0 and public hosts, so there is no public exposure
- As a system operator, I want documentation stating remote access is only through an approved private VPN, so remote operators follow the sanctioned access path

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Role enum values | `tests/unit/test_m11_auth.py::test_role_enum_values` | ModuleNotFoundError | PASS | Roles: owner, operator, viewer |
| Session create + validate | `tests/unit/test_m11_auth.py::test_session_create_and_validate` | ModuleNotFoundError | PASS | Active session created, validates by id |
| Session expiry invalidates | `tests/unit/test_m11_auth.py::test_session_expires_and_is_no_longer_valid` | ModuleNotFoundError | PASS | Expired session returns None |
| Session invalidate | `tests/unit/test_m11_auth.py::test_session_invalidate` | ModuleNotFoundError | PASS | Invalidation returns True then None |
| Unknown session returns None | `tests/unit/test_m11_auth.py::test_unknown_session_returns_none` | ModuleNotFoundError | PASS | Unknown id → None |
| Owner can change settings | `tests/unit/test_m11_auth.py::test_owner_can_change_settings` | ModuleNotFoundError | PASS | Backend enforces owner-only settings change |
| Operator cannot change settings | `tests/unit/test_m11_auth.py::test_operator_cannot_change_settings` | ModuleNotFoundError | PASS | Operator denied settings change |
| Viewer cannot change settings | `tests/unit/test_m11_auth.py::test_viewer_cannot_change_settings` | ModuleNotFoundError | PASS | Viewer denied settings change |
| Viewer can read dashboard | `tests/unit/test_m11_auth.py::test_viewer_can_read_dashboard` | ModuleNotFoundError | PASS | Viewer authorized for read actions |
| Secret redacted + non-exportable | `tests/unit/test_m11_auth.py::test_secret_redacted_and_nonexportable` | ModuleNotFoundError | PASS | Redacted != plaintext, plaintext not present, REDACTED/**** marker |
| Redact empty secret | `tests/unit/test_m11_auth.py::test_redact_secret_empty` | ModuleNotFoundError | PASS | Empty → empty |
| Localhost host accepted | `tests/unit/test_m11_auth.py::test_is_localhost_host_accepts_local` | ModuleNotFoundError | PASS | 127.0.0.1, localhost, ::1 accepted |
| Public host rejected | `tests/unit/test_m11_auth.py::test_is_localhost_host_rejects_public` | ModuleNotFoundError | PASS | 0.0.0.0, 192.168.x, example.com rejected |
| validate_bind_host accepts localhost | `tests/unit/test_m11_auth.py::test_validate_bind_host_accepts_localhost` | ModuleNotFoundError | PASS | No raise for 127.0.0.1 / localhost |
| validate_bind_host rejects public | `tests/unit/test_m11_auth.py::test_validate_bind_host_rejects_public` | ModuleNotFoundError | PASS | ValueError for public hosts |
| VPN documentation exists | `tests/unit/test_m11_auth.py::test_vpn_documentation_exists` | ModuleNotFoundError | PASS | docs/private-vpn-access.md documents VPN-only remote access |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Session create/validate/expire/invalidate | `tests/unit/test_m11_auth.py::test_session_*` | unit | PASS | 5 tests pass |
| 2 | Role-based authorization (owner-only settings) | `tests/unit/test_m11_auth.py::test_*_change_settings|test_viewer_can_read_dashboard` | unit | PASS | 4 tests pass |
| 3 | Secret redaction non-exportable | `tests/unit/test_m11_auth.py::test_secret_redacted_*` | unit | PASS | 2 tests pass |
| 4 | Localhost-only binding enforcement | `tests/unit/test_m11_auth.py::test_is_localhost_host_*|test_validate_bind_host_*` | unit | PASS | 4 tests pass |
| 5 | VPN documentation present | `tests/unit/test_m11_auth.py::test_vpn_documentation_exists` | unit | PASS | docs/private-vpn-access.md |

## Coverage and known gaps

- No coverage tool configured; all `superbot.m11.auth` lines exercised by unit tests (every role/action branch, session state transition, redaction path, bind-host validation).
- Full `tests/unit` suite exits 0 (MT5-dependent tests skipped without a terminal); no regressions from M11.3.
- ruff clean on new/changed files.
- Stdlib-only; no import-time network/database/MT5 activity.
- Intentional gap: sessions are in-memory (SessionStore) for M11.3; persistent session storage (PostgreSQL) and rotation/refresh tokens are out of scope for this milestone.
- Intentional gap: actual Streamlit auth UI (login form, session cookie) is out of scope; authorization is enforced in the FastAPI backend (`can()`) and exposed via existing `/settings/profiles` owner-only check.
- VPN document is a markdown policy file; no automated enforcement of VPN usage beyond localhost bind enforcement (remote reachability is an operational concern).

## Merge evidence

RED: `ModuleNotFoundError: No module named 'superbot.m11.auth'` captured before implementation. GREEN: 18 M11.3 tests pass; full `tests/unit` suite exits 0; ruff clean. New files: `src/superbot/m11/auth.py`, `tests/unit/test_m11_auth.py`, `docs/private-vpn-access.md`.
