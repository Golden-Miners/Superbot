# Superbot

Superbot is a local-first, deterministic AI trading research and simulation application. It connects to MetaTrader 5 (MT5) demo accounts for market data and trade execution, with AI signal generation via Ollama used **only for decision making** — never for trade execution or position management.

## Architecture

- **Ollama** → Signal generation (decision making only)
- **ExecutionPermissionService** → 9 safety gates: DEMO-only, server allowlist, rate limiting, trade confirmation, risk limits, market data freshness, symbol mapping, account verification
- **MT5ExecutionAdapter** → Order submission to MT5 demo terminal
- **Deterministic by design**: All broker writes route through authorization gates; fail-closed if any gate fails

## Quick Start

### Prerequisites

- Python 3.14+
- MetaTrader 5 terminal installed and running (demo account)
- `metatrader5` Python package: `pip install MetaTrader5`
- Optional: Ollama running locally for AI signal generation

### Install

```bash
cd C:\SuperBot
pip install -e .
pip install pytest ruff streamlit fastapi
```

### Run Tests

```bash
pytest tests/unit/ -v
```

### Launch Dashboard

```bash
python -m superbot.m11.launch --mode dashboard
```

Opens Streamlit UI at `http://127.0.0.1:8501`.

### Launch Trading Loop (Demo Only)

```bash
python -m superbot.m11.launch --mode trading
```

Connects to MT5, enables DEMO execution, and runs the autonomous trading loop. **No live trading** — `LIVE_TRADING_ENABLED` defaults to `False` and only DEMO accounts on approved XM servers are permitted.

### Launch Both (Dashboard + Trading)

```bash
python -m superbot.m11.launch --mode both
```

## Safety

- All broker writes require explicit authorization through `ExecutionPermissionService`
- `LIVE_TRADING_ENABLED = False` by default
- Only DEMO accounts on approved XM demo servers
- Trade confirmation required (owner role) before any order is sent
- Fail-closed: any gate failure blocks execution

## Project Structure

```
src/superbot/
  ai/            # AI signal generation (Ollama) + execution pipeline
  execution/     # Signal-to-order translation pipeline
  engine/        # Engine POC comparison, scoring, selection
  m11/           # MT5 integration: data provider, adapter, trading loop, UI
  m10/           # Scheduler/supervisor/operations
  m9/            # Local AI agents
  persistence/   # Storage, audit, backup, recovery
  risk/          # Portfolio/risk management
  simulation/    # Deterministic simulator and accounting
  strategy/      # Strategy rules and signals
  data/          # Data contracts and quality pipeline
  contracts/     # Domain contracts (InstrumentSpec, OHLCVBar)
  supervisor/    # Health model and startup/shutdown
  observability/ # Structured logging and correlation IDs
tests/
  unit/          # Unit tests (189+ passing)
  e2e/           # End-to-end browser tests
  integration/   # MT5 terminal integration tests
docs/adr/        # Architecture decision records
```

## License

Private — not for public distribution.