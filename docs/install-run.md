# Local install and run — Superbot dashboard (M12.3 known-good configuration)

## 1. Prerequisites (verified)

- Python 3.14.7 (Windows)
- pip
- `git` (optional, for checkout)

No live MT5 terminal, PostgreSQL, model runtime, or broker credentials are required to run the dashboard — all dashboard state is deterministic, labeled internal simulation / research, and binds localhost only.

## 2. Install dependencies

From the repository root (`C:\SuperBot`):

```powershell
pip install -e .
```

This installs the runtime dependencies declared in `pyproject.toml`:

```
fastapi>=0.100,<1
pyarrow==26.0.*
plotly>=5,<9
streamlit>=1.30,<2
uvicorn>=0.24,<1
```

Dev tooling (already installed in this environment):

```
pytest>=8.0,<10
ruff>=0.17,<1
```

Playwright + pytest-playwright + a cached Chromium browser are additionally required for the E2E browser tests (`tests/e2e`), but not for running the app.

## 3. Run the application

All Superbot Python imports require `PYTHONPATH=src`.

### Streamlit dashboard (UI)

```powershell
$env:PYTHONPATH="src"
streamlit run src/superbot/m11/app.py `
  --server.port 8501 `
  --server.address 127.0.0.1 `
  --server.headless true `
  --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501`. The app binds `127.0.0.1` only — never `0.0.0.0` or a public interface. Remote access is only via an approved private VPN (see `docs/private-vpn-access.md`).

### FastAPI API (backend)

The API lives in `src/superbot/m11/api.py` (`create_app()`). It can be run with uvicorn if installed, or exercised via `fastapi.testclient.TestClient` (used by `tests/unit/test_m11_api.py`):

```powershell
$env:PYTHONPATH="src"
python -c "from superbot.m11.api import create_app; app=create_app(); print(app.routes | Select-Object -First 1 -ExpandProperty path)"
```

OpenAPI docs (localhost only): `http://127.0.0.1:8000/openapi.json` when served via uvicorn.

## 4. Run the test suite

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/unit -q            # unit suites (all pass)
python -m pytest tests/e2e -q            # browser suites (requires Chromium)
python -m ruff check src/ tests/         # static analysis (clean)
```

Some `tests/unit` cases require a live MT5 terminal and are skipped when unavailable. E2E tests start the Streamlit app on a free localhost port and drive real Chromium.

## 5. Known-good configuration (verified in this session)

| Setting | Value |
|---|---|
| Python | 3.14.7 |
| fastapi | 0.143.0 |
| pyarrow | 26.0.0 |
| streamlit | 1.66.1 |
| plotly | 7.1.0 |
| pytest | 9.1.1 |
| ruff | clean (line-length 100) |
| Bind host | `127.0.0.1` / `localhost` only (`validate_bind_host` rejects public hosts) |
| API OpenAPI server | `http://127.0.0.1:8000` (localhost only) |
| Roles | owner / operator / viewer (backend-enforced via `SessionStore.can`) |
| Settings changes | owner-only; viewer/operator read-only |
| Secrets | redacted, non-exportable (`redact_secret`) |
| Live orders | disabled in V1; no enable-live-order control |
| Data labels | `internal_simulation` / `synthetic_fixture`; never implies live broker data |

## 6. Notes

- The dashboard surfaces (overview, data explorer, jobs, strategy/signal workbench, validation/experiments, portfolio/risk, audit/experiment library, settings/profiles) render deterministic fixtures labeled internal simulation — no fake success, no live-order controls.
- MT5/PostgreSQL/model-runtime integration is out of scope for V1 and gated behind live-terminal availability (skipped in tests).
