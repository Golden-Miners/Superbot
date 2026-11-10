"""V2.7 — Superbot Unified Launcher.

Single entry point for running Superbot:

  * Dashboard:  python -m superbot.m11.launch --mode dashboard
  * Trading:    python -m superbot.m11.launch --mode trading
  * Both:       python -m superbot.m11.launch --mode both

Default mode is 'dashboard'.  The trading loop runs in a background thread
when launched with --mode both, allowing the Streamlit dashboard to remain
responsive.

Stdlib-only except for MetaTrader5 import (lazy, import-safe) and Streamlit.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time

from superbot.m11.auth import SessionStore
from superbot.m11.execution_authorizer import ExecutionPermissionService
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider
from superbot.m11.trading_loop import TradingLoop


def _setup_mt5() -> tuple[MT5DataProvider, ExecutionPermissionService, MT5ExecutionAdapter]:
    """Connect to MT5, verify DEMO account, and wire up execution services.

    Returns (provider, auth, adapter) on success; raises SystemExit(1)
    on any failure.
    """
    provider = MT5DataProvider()
    if not provider.connect():
        print("ERROR: Could not connect to MT5 terminal.", file=sys.stderr)
        raise SystemExit(1)

    account_info = provider.get_account_info()
    if account_info is None:
        print("ERROR: Could not read MT5 account info.", file=sys.stderr)
        raise SystemExit(1)

    trade_mode = account_info.get("trade_mode")
    server = account_info.get("server", "")
    if trade_mode != 0:
        print(f"ERROR: Account is not DEMO (trade_mode={trade_mode}).", file=sys.stderr)
        raise SystemExit(1)
    demo_servers = ExecutionPermissionService.DEFAULT_DEMO_SERVERS
    if server not in demo_servers:
        print(
            f"ERROR: Account server '{server}' is not an approved demo server.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(
        f"Connected to MT5 demo: login={account_info.get('login')}, "
        f"server={server}, balance={account_info.get('balance')}"
    )

    auth = ExecutionPermissionService(mt5_data_provider=provider)
    auth.LIVE_TRADING_ENABLED = True

    session_store = SessionStore()
    session, token = session_store.create_session(role="owner")
    auth.enable_execution(token, session_store)

    adapter = MT5ExecutionAdapter(mt5_data_provider=provider, auth=auth)

    return provider, auth, adapter


def _run_dashboard() -> None:
    """Launch the Streamlit dashboard."""
    import subprocess
    import os

    app_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "app.py"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    subprocess.run(
        [
            "streamlit",
            "run",
            app_path,
            "--server.port=8501",
            "--server.address=127.0.0.1",
        ],
        env=env,
    )


def _run_trading_loop(provider: MT5DataProvider, auth: ExecutionPermissionService, adapter: MT5ExecutionAdapter) -> None:
    """Run the autonomous trading loop."""
    loop = TradingLoop(
        mt5_data_provider=provider,
        poll_interval_seconds=30.0,
        min_order_interval_seconds=60.0,
    )
    loop.run()


def main() -> int:
    """Unified entry point for Superbot.

    Modes:
        dashboard  - Streamlit UI (default)
        trading    - Autonomous MT5 execution loop
        both       - Dashboard + trading loop in background thread
    """
    parser = argparse.ArgumentParser(description="Superbot launcher")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "trading", "both"],
        default="dashboard",
        help="Run mode (default: dashboard)",
    )
    args = parser.parse_args()

    if args.mode in ("trading", "both"):
        provider, auth, adapter = _setup_mt5()
        if args.mode == "trading":
            _run_trading_loop(provider, auth, adapter)
            return 0

    if args.mode in ("dashboard", "both"):
        if args.mode == "both":
            # Start trading loop in a daemon thread so dashboard stays responsive
            provider, auth, adapter = _setup_mt5()
            t = threading.Thread(
                target=_run_trading_loop,
                args=(provider, auth, adapter),
                daemon=True,
            )
            t.start()
        _run_dashboard()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())