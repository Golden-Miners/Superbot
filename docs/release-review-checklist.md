# Release review and human approval (M12.5)

## Purpose

Gate the Superbot V1 release behind a documented review: all mandatory gates passed, evidence preserved, no critical/high unresolved defect, no live trading. Requires explicit human approval before any release-stage promotion.

## Release review checklist

| # | Gate | Evidence location | Status |
|---|---|---|---|
| 1 | Unit + integration + e2e suites all pass | `tests/unit`, `tests/e2e`; `python -m pytest` exits 0 | |
| 2 | Static analysis clean | `python -m ruff check src/ tests/` — "All checks passed" | |
| 3 | Dependency/security scan | `docs/install-run.md` §5; no hardcoded secrets, no public binding | |
| 4 | All 8 dashboard surfaces render backend-driven state | `tests/e2e/test_m11_browser.py`; screenshots in `tests/e2e/screenshots/` | |
| 5 | No live-order controls; `live orders enabled: false` | `src/superbot/m11/api.py`, `src/superbot/m11/ui.py` | |
| 6 | Localhost-only binding enforced | `validate_bind_host`; OpenAPI server `http://127.0.0.1:8000` | |
| 7 | Secrets redacted and non-exportable | `redact_secret`, `secret_redacted: true` | |
| 8 | Authorization backend-enforced (owner-only settings) | `SessionStore.can`; 403 for non-owner | |
| 9 | Data labeled internal simulation / synthetic (not live) | `STATE` fixtures; source labels | |
| 10 | TDD evidence reports preserved | `docs/tdd/m11-*.tdd.md` | |
| 11 | Install/run docs present | `docs/install-run.md`, `docs/migration-laptop-to-desktop.md` | |
| 12 | VPN / remote-access policy documented | `docs/private-vpn-access.md` | |

## Explicit human approval

No release-stage promotion occurs without explicit human sign-off. Record:

- Approver name / role:
- Date:
- Gates reviewed (all above):
- Decision (APPROVED / REJECTED / CONDITIONAL):
- Conditions (if any):
- Signature:

## Release conditions

- **No live trading.** The release does not enable or include live-order execution, broker connectivity, or demo trading.
- **No public exposure.** The dashboard binds localhost only; remote access only via approved private VPN.
- **Evidence preserved.** Test results, screenshots, TDD reports, and this checklist are retained with the release artifact.
- **Rollback path.** If any gate fails post-release, roll back to the previous known-good configuration (`docs/install-run.md` §5) and re-run `tests/unit` + `tests/e2e` + `ruff check`.

## Doc updates

All release-related docs live under `docs/`:
- `docs/install-run.md` — local install/run + known-good configuration
- `docs/migration-laptop-to-desktop.md` — laptop-to-desktop migration
- `docs/private-vpn-access.md` — remote access policy
- `docs/tdd/m11-*.tdd.md` — per-milestone TDD evidence
- `task.md` — milestone status ledger

Update `task.md` and this checklist when any gate, dependency, or configuration changes.
