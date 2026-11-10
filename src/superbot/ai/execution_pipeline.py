"""AI execution pipeline (V2.9).

Wires AI signal generation through ExecutionPermissionService to
MT5ExecutionAdapter for broker submission.

All write operations route through ExecutionPermissionService for
authorization. No broker writes occur without explicit authorization.

Read-only by default; broker writes only when execution mode is
DEMO_EXECUTION and all authorization checks pass.

Stdlib-only.
"""

from __future__ import annotations

from decimal import Decimal

from superbot.ai.ai_config import AIConfig
from superbot.ai.signal_generator import AISignal
from superbot.m11.execution_authorizer import ExecutionPermissionService, OrderRequest
from superbot.m11.mt5_adapter import MT5ExecutionAdapter
from superbot.m11.mt5_data_provider import MT5DataProvider


class AIExecutionPipeline:
    """End-to-end AI execution pipeline.

    Wires AI signal generation through ExecutionPermissionService to
    MT5ExecutionAdapter for broker submission.

    All write operations route through ExecutionPermissionService for
    authorization. No broker writes occur without explicit authorization.

    Read-only by default; broker writes only when execution mode is
    DEMO_EXECUTION and all authorization checks pass.

    Stdlib-only except for MetaTrader5 import (lazy, import-safe) via
    MT5DataProvider.
    """

    def __init__(
        self,
        mt5_data_provider: MT5DataProvider,
        auth: ExecutionPermissionService,
        adapter: MT5ExecutionAdapter,
    ) -> None:
        self.mt5_data_provider = mt5_data_provider
        self.auth = auth
        self.adapter = adapter

    def execute_signal(
        self,
        signal: AISignal,
        token: str,
        session_store,
    ):
        """Submit an AI signal through the full authorization pipeline.

        Translates an AISignal into an OrderRequest, authorizes it through
        ExecutionPermissionService (all safety gates), and if authorized
        submits it to MT5 via MT5ExecutionAdapter.submit_order().

        Args:
            signal: The AISignal produced by the AI signal generator.
            token: Session token for authorization.
            session_store: SessionStore for token validation.

        Returns:
            OrderResult — allowed=True if order submitted to MT5,
            allowed=False if rejected at any gate.
        """
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=signal.side,
            volume=signal.volume,
            price=signal.price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            order_type="market",
            client_order_id=f"ai:{signal.symbol}:{signal.side}:{signal.timestamp_utc.isoformat()}",
        )

        auth_result = self.auth.authorize(
            order_request=order_request,
            token=token,
            session_store=session_store,
        )

        if not auth_result.allowed:
            return auth_result

        return self.adapter.submit_order(
            symbol=order_request.symbol,
            side=order_request.side,
            volume=order_request.volume,
            price=order_request.price,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
            order_type=order_request.order_type,
            client_order_id=order_request.client_order_id,
            token=token,
            session_store=session_store,
        )