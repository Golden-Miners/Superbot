"""RED tests for MT5 Execution Adapter launch script (launch.py).

Covers:
- launch.py module can be imported
- main() function exists and is callable
- main() creates MT5DataProvider and connects
- main() creates ExecutionPermissionService with LIVE_TRADING_ENABLED=True
- main() creates MT5ExecutionAdapter
- main() calls loop.run() on TradingLoop

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from superbot.m11.execution_authorizer import ExecutionPermissionService
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider


def test_launch_module_imports():
    """launch.py module can be imported without errors."""
    import superbot.m11.launch  # noqa: F401


def test_main_function_exists():
    """main() function exists and is callable."""
    from superbot.m11.launch import main

    assert callable(main)


def test_main_creates_mt5_data_provider():
    """main() creates MT5DataProvider and connects."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,  # DEMO
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True

    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        result = launch_mod.main(["--mode", "dashboard"])
        mock_provider.connect.assert_called_once()
        assert result == 0


def test_main_creates_execution_authorizer():
    """main() creates ExecutionPermissionService with the provider."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_auth.LIVE_TRADING_ENABLED = False
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        launch_mod.main(["--mode", "trading"])
        launch_mod.ExecutionPermissionService.assert_called_once_with(
            mt5_data_provider=mock_provider
        )
        assert mock_auth.LIVE_TRADING_ENABLED is False


def test_main_creates_mt5_adapter():
    """main() creates MT5ExecutionAdapter with provider and auth."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        launch_mod.main(["--mode", "trading"])
        launch_mod.MT5ExecutionAdapter.assert_called_once_with(
            mt5_data_provider=mock_provider, auth=mock_auth
        )


def test_main_calls_loop_run():
    """main() calls loop.run() on TradingLoop."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        launch_mod.main(["--mode", "trading"])

    mock_loop.run.assert_called_once()


def test_main_returns_zero_on_success():
    """main() returns 0 when MT5 connection succeeds."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        result = launch_mod.main(["--mode", "dashboard"])

    assert result == 0


def test_main_returns_non_zero_on_connection_failure():
    """main() returns non-zero when MT5 connection fails."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = False

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        result = launch_mod.main(["--mode", "dashboard"])
        assert result != 0


def test_main_enable_execution_called():
    """main() calls enable_execution on auth service."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop):

        launch_mod.main(["--mode", "trading"])
        mock_auth.enable_execution.assert_called_once()


def test_main_session_store_created():
    """main() creates SessionStore for authorization."""
    import superbot.m11.launch as launch_mod

    mock_provider = MagicMock()
    mock_provider.connect.return_value = True
    mock_provider.get_account_info.return_value = {
        "login": 12345,
        "server": "XMGlobal-MT5 7",
        "trade_mode": 0,
        "balance": 10000.0,
        "equity": 10000.0,
    }

    mock_auth = MagicMock()
    mock_auth.is_execution_allowed.return_value = True
    mock_adapter = MagicMock()
    mock_loop = MagicMock()
    mock_loop.run.return_value = 0

    with patch.object(launch_mod, "MT5DataProvider", return_value=mock_provider), \
         patch.object(launch_mod, "ExecutionPermissionService", return_value=mock_auth), \
         patch.object(launch_mod, "MT5ExecutionAdapter", return_value=mock_adapter), \
         patch.object(launch_mod, "TradingLoop", return_value=mock_loop), \
         patch.object(launch_mod, "SessionStore") as mock_ss:

        mock_ss.return_value.create_session.return_value = ("session", "token")
        launch_mod.main(["--mode", "trading"])
        mock_ss.assert_called_once()
