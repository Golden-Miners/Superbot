# Private VPN Access — Superbot Dashboard

## Remote access policy

The Superbot dashboard (Streamlit UI + FastAPI API) binds **localhost only**
(`127.0.0.1`, `localhost`, `::1`) and must never be exposed on a public
network interface (`0.0.0.0` or any public IP/hostname). There is no public
exposure of the dashboard, API, or any live-order controls in this scope.

## Approved access method

Remote access to the dashboard is permitted **only through an approved private
VPN**. Operators must connect to the organization's private VPN before
accessing `http://127.0.0.1:8000` (API) or the Streamlit UI port from a remote
machine. Direct internet exposure, port forwarding, ngrok-style tunnels, or
binding to `0.0.0.0` are prohibited.

## Enforcement

- The FastAPI app advertises only `http://127.0.0.1:8000` in its OpenAPI
  server list (see `src/superbot/m11/api.py`).
- `validate_bind_host()` rejects any non-localhost bind host at startup.
- Sensitive settings changes require the `owner` role; viewer/operator roles
  are authorized to read only.
- Secrets are redacted and non-exportable.

## Roles

- `owner`: full access, including changing sensitive settings.
- `operator`: read dashboard/health/data explorer; read audit; cancel jobs;
  update strategy.
- `viewer`: read-only access to dashboard/health/data explorer.

Hiding a UI button is insufficient — authorization is enforced on the backend.
