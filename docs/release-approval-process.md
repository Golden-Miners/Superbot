# Release Approval Process — M12.5 / Superbot V1

**Status:** Pending human operator configuration
**Protected branch:** `master`
**Remote:** `https://github.com/Golden-Miners/Superbot.git`

## Approval Configuration

| Setting | Value |
|---------|-------|
| Authorized operator | Named individual (to be identified) |
| Communication channel | GitHub PR review |
| Required evidence | Full audit package (test results + TDD reports + security scan + lint results) |
| Dual approval | No (single approver sufficient) |
| Rejection workflow | Fix and resubmit |
| Auto-block enforcement | Hybrid (automated checks + manual approval) |

## Required GitHub Branch Protection Settings

Configure these settings on GitHub at:
`https://github.com/Golden-Miners/Superbot/settings/branches`

### Branch protection rule for `main`/`master`:

| Setting | Value |
|---------|-------|
| Require a pull request before merging | **Enabled** |
| Require approvals | **1** (single approver) |
| Dismiss stale approvals on new commits | **Enabled** |
| Require review from code owners | **Disabled** |
| Require status checks before merging | **Enabled** |
| Required status checks | All CI tests must pass |
| Require branches to be up to date before merging | **Enabled** |
| Restrict pushes to matching branches | **Enabled** (only authorized users) |
| Allow force pushes | **Disabled** |
| Allow deletions | **Disabled** |
| Lock branch | **Disabled** |

### Required status checks (all must pass):

- `pytest` — Unit and integration tests
- `ruff` — Static analysis/linting
- `playwright` — E2E browser tests

## Release Approval Workflow

### 1. Prepare release
1. Ensure all tests pass: `python -m pytest tests/unit tests/e2e`
2. Ensure ruff is clean: `python -m ruff check src/ tests/`
3. Ensure ruff format is clean: `python -m ruff format --check src/ tests/`
4. Verify no secrets in code: security scan shows no hardcoded credentials
5. Verify no live-order controls exist in the codebase
6. Verify localhost-only binding (no `0.0.0.0`)

### 2. Create PR
1. Create a PR from `repair/v1-stabilization` (or release branch) to `master`
2. Include all TDD evidence reports in the PR description:
   - `docs/tdd/m11-2-dashboard-surfaces.tdd.md`
   - `docs/tdd/m11-3-auth-sessions-roles-redaction-local-binding-vpn.tdd.md`
   - `docs/tdd/m11-4-browser-tests-accessibility-screenshots.tdd.md`
   - `docs/tdd/m11-2-dashboard-surfaces.tdd.md`
   - `docs/tdd/phase-1-restore-source-integrity.tdd.md`
   - `docs/tdd/phase-2-security-fixes.tdd.md`
   - `docs/tdd/phase-3-backup-security.tdd.md`
   - `docs/tdd/phase-4-2-synthetic-vs-live-labels.tdd.md`
   - `docs/tdd/phase-5-cross-component-integration.tdd.md`

### 3. Request review
1. Assign the designated human operator as reviewer
2. Wait for approval
3. If rejected: fix issues and resubmit PR

### 4. Merge
1. Once approved, merge the PR to `master`
2. Tag the release: `git tag v1.0.0 && git push origin v1.0.0`
3. Document the release in `CHANGELOG.md`

## Emergency Rollback

If a release causes issues:
1. Revert the PR on GitHub
2. Or: `git revert <commit-hash> && git push origin master`
3. Document the rollback reason in the ADR log

## No-Live-Trading Confirmation

The following are confirmed absent from the codebase:
- ✅ No live-order submission methods (MT5 adapter is read-only)
- ✅ No public network binding (localhost-only)
- ✅ No hardcoded secrets or credentials
- ✅ Secrets are redacted in all outputs
- ✅ Owner-only settings changes enforced server-side

## Next Steps

1. **Identify the designated human operator** — who will be the release approver?
2. **Configure GitHub branch protection** — go to GitHub repo settings → Branches → Add rule for `master`
3. **Create the release PR** from `repair/v1-stabilization` to `master`
4. **Obtain approval** from the designated operator
5. **Merge and tag** the release
