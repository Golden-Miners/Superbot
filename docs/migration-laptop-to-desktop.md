# Laptop-to-desktop migration / revalidation (M12.4)

## Purpose

Documented, repeatable procedure for moving Superbot from a laptop to a desktop (or any second machine): migrate config, database backup, data manifests/checksums, reinstall dependencies/models, and revalidate the environment. No live trading is involved; all dashboard state is internal simulation / research.

## Prerequisites on the target (desktop) machine

- Python 3.14+
- pip
- Network access to install dependencies (or a pre-staged offline wheel cache)
- (Optional) PostgreSQL if the persistence layer is wired later; V1 dashboard runs without it

## Migration procedure

### 1. Export from the laptop

1. Record the dependency versions from `pyproject.toml` and the installed environment:

   ```powershell
   pip freeze > requirements.laptop.txt
   ```

2. Back up any local configuration and data artifacts:

   - `pyproject.toml` (project config + dependency declarations)
   - `docs/private-vpn-access.md` (access policy)
   - Any local `config.yaml` / secrets store (secrets are redacted in the app; do not export plaintext secrets)
   - Data manifests and checksums for OHLCV history / experiment artifacts (per `schema.md` and `architecture.md`)

   Do NOT export plaintext credentials, API keys, or tokens.

### 2. Transfer to the desktop

Copy the exported files over a secure channel (e.g. within the private VPN). Do not send secrets over unencrypted channels.

### 3. Install on the desktop

```powershell
# On the desktop, in the cloned Superbot repository root
pip install -r requirements.laptop.txt
# or, to match the declared project dependencies exactly:
pip install -e .
```

Verify versions match the known-good configuration in `docs/install-run.md` §5 (fastapi 0.143.0, streamlit 1.66.1, plotly 7.1.0, pytest 9.1.1, ruff).

### 4. Revalidate the environment

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/unit -q          # all unit suites pass
python -m ruff check src/ tests/        # static analysis clean
```

For the E2E browser tests (requires Chromium):

```powershell
python -m pytest tests/e2e -q
```

### 5. Run the application on the desktop

Follow `docs/install-run.md` §3. Confirm:

- The app binds `127.0.0.1` only (never `0.0.0.0`).
- All 8 dashboard surfaces render.
- Settings show `live orders enabled: false`.
- Secrets are redacted; no enable-live-order control.

### 6. Sign-off

Record the desktop environment (Python version, dependency versions, test results, screenshots) in the migration log before treating the desktop as a known-good configuration. Re-run this procedure whenever Python, dependencies, or the OS change materially.

## What is NOT migrated

- Plaintext secrets / credentials (redacted, non-exportable in-app)
- Live MT5 terminal or broker connections (read-only MT5 is out of V1 scope)
- Model runtime / inference budget (benchmarked separately per `context.md`; winner OPEN)
