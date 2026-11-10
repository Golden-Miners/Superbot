"""Signal-to-order pipeline (schema.md section 7.x).

Wires strategy signal analysis to broker order execution through the
ExecutionPermissionService, preserving all safety gates:

- Hard Gate #1: Account re-verified as DEMO on every order (in authorize())
- Hard Gate #3: LIVE_TRADING_ENABLED gate (in authorize())
- Hard Gate #4: Rate limiting — 1 order per minute (in mark_confirmation_consumption())
- Hard Gate #5: Trade confirmation — owner must call confirm_order() before
  any order is sent to MT5. No fully autonomous execution.

Pipeline flow:
    signal analysis → translate → authorize (pending confirmation)
                                          ↓
                                    owner confirms (confirm_order())
                                          ↓
                                    send_confirmed_order() → MT5 terminal
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from superbot.m11.execution_authorizer import (
    ExecutionPermissionService,
    OrderRequest,
)
from superbot.risk.signal_ranking import Signal
from superbot.strategy.trend_following import PullbackSignal


@dataclass(frozen=True)
class OrderCandidate:
    """A candidate order translated from a signal, awaiting authorization."""

    symbol: str
    side: str  # "buy" or "sell"
    volume: Decimal
    price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    order_type: str = "market"
    client_order_id: str | None = None
    source_signal_id: str | None = None
    source_strategy: str | None = None


class SignalToOrderRequestTranslator:
    """Translates PullbackSignal + ranked Signal into an OrderCandidate.

    Mapping:
    - PullbackSignal.signal_type → OrderCandidate.side
      ("entry_long" → "buy", "entry_short" → "sell")
    - PullbackSignal.entry_price → OrderCandidate.price
    - PullbackSignal.stop_price → OrderCandidate.stop_loss
    - Signal.symbol → OrderCandidate.symbol
    - Signal.size → OrderCandidate.volume (falls back to default_volume)
    - Default take-profit: 2:1 reward-to-risk ratio
      (entry ± (entry − stop) × 2, direction-dependent)
    """

    def __init__(
        self,
        default_volume: Decimal = Decimal("0.01"),
    ) -> None:
        self.default_volume = default_volume

    def translate(
        self,
        pullback_signal: PullbackSignal,
        ranked_signal: Signal,
        strategy_id: str = "trend_following_v1",
    ) -> OrderCandidate:
        """Translate a signal pair into an OrderCandidate.

        Args:
            pullback_signal: The entry signal from trend detection.
            ranked_signal: The ranked signal with symbol, side, size.
            strategy_id: Strategy identifier for the client_order_id prefix.

        Returns:
            OrderCandidate ready for authorization.
        """
        side = "buy" if pullback_signal.signal_type == "entry_long" else "sell"
        volume = ranked_signal.size if ranked_signal.size > 0 else self.default_volume
        price = pullback_signal.entry_price
        stop_loss = pullback_signal.stop_price

        # Default take-profit: 2:1 reward-to-risk
        take_profit: Decimal | None = None
        if price is not None and stop_loss is not None and stop_loss > Decimal(0):
            risk = abs(price - stop_loss)
            if risk > Decimal(0):
                if side == "buy":
                    take_profit = price + (risk * Decimal(2))
                else:
                    take_profit = price - (risk * Decimal(2))

        return OrderCandidate(
            symbol=ranked_signal.symbol,
            side=side,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_type="market",
            client_order_id=f"{strategy_id}:{ranked_signal.symbol}:{side}",
            source_signal_id=getattr(pullback_signal, "signal_id", None),
            source_strategy=strategy_id,
        )


@dataclass(frozen=True)
class SubmissionResult:
    """Result of submitting a signal through the pipeline."""

    status: str  # "pending_confirmation", "rejected", "submitted", "error"
    reason: str | None = None
    confirmation_key: str | None = None
    symbol: str | None = None
    side: str | None = None
    volume: str | None = None
    price: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    evidence: dict | None = None


class OrderSubmissionPipeline:
    """Pipeline: signal → translate → authorize → pending confirmation
    → owner confirms → send to MT5.

    Hard Gate #5 is preserved: orders require explicit owner confirmation
    via confirm_order() before being sent to MT5. No fully autonomous
    execution without explicit human approval.

    Usage:
        # Step 1: Generate signal from analysis
        signal = trend_following_entry(bars, trend_spec, pullback_spec)
        ranked = SignalRankingService().rank_signals([Signal(...)])[0]

        # Step 2: Submit through pipeline (returns pending_confirmation)
        result = pipeline.submit_signal(signal, ranked, token, session_store)
        # result.status == "pending_confirmation"
        # result.confirmation_key → pass to owner for confirmation

        # Step 3: Owner confirms (explicit human action)
        pipeline.auth.confirm_order(token, result.confirmation_key, session_store)

        # Step 4: Send to MT5
        final = pipeline.confirm_and_send(
            result.confirmation_key, token, session_store
        )
        # final.status == "submitted" if broker accepted
    """

    def __init__(
        self,
        auth: ExecutionPermissionService,
        adapter,
        translator: SignalToOrderRequestTranslator | None = None,
    ) -> None:
        self.auth = auth
        self.adapter = adapter
        self.translator = translator or SignalToOrderRequestTranslator()
        # confirmation_key → OrderRequest (stored until confirmed and sent)
        self._pending: dict[str, OrderRequest] = {}

    def submit_signal(
        self,
        pullback_signal: PullbackSignal,
        ranked_signal: Signal,
        token: str,
        session_store,
        strategy_id: str = "trend_following_v1",
    ) -> SubmissionResult:
        """Submit a signal through the full authorization pipeline.

        Translates the signal to an OrderRequest, calls
        ExecutionPermissionService.authorize() (all safety gates apply),
        and stores the pending order. Returns a SubmissionResult with
        status "pending_confirmation" and a confirmation_key that the
        owner must pass to confirm_order() before the order is sent.

        Args:
            pullback_signal: Entry signal from trend_following.
            ranked_signal: Ranked signal with symbol, side, size.
            token: Session token for authorization.
            session_store: SessionStore for token validation.
            strategy_id: Strategy identifier for client_order_id.

        Returns:
            SubmissionResult with status and confirmation_key (if pending).
        """
        # Translate signal to order candidate
        candidate = self.translator.translate(
            pullback_signal, ranked_signal, strategy_id
        )

        # Build OrderRequest
        order_request = OrderRequest(
            symbol=candidate.symbol,
            side=candidate.side,
            volume=candidate.volume,
            price=candidate.price,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            order_type=candidate.order_type,
            client_order_id=candidate.client_order_id,
        )

        # Authorize through ExecutionPermissionService (all safety gates)
        auth_result = self.auth.authorize(
            order_request=order_request,
            token=token,
            session_store=session_store,
        )

        if not auth_result.allowed:
            return SubmissionResult(
                status="rejected",
                reason=auth_result.reason or "authorization denied",
                evidence=auth_result.evidence,
            )

        # Order authorized — store for later confirmation+send
        confirmation_key = auth_result.evidence.get("confirmation_key")
        if confirmation_key is None:
            return SubmissionResult(
                status="error",
                reason="authorization succeeded but no confirmation key returned",
                evidence=auth_result.evidence,
            )
        self._pending[confirmation_key] = order_request

        return SubmissionResult(
            status="pending_confirmation",
            confirmation_key=confirmation_key,
            symbol=candidate.symbol,
            side=candidate.side,
            volume=str(candidate.volume),
            price=str(candidate.price) if candidate.price else None,
            stop_loss=str(candidate.stop_loss) if candidate.stop_loss else None,
            take_profit=str(candidate.take_profit) if candidate.take_profit else None,
            evidence=auth_result.evidence,
        )

    def confirm_and_send(
        self,
        confirmation_key: str,
        token: str,
        session_store,
    ) -> SubmissionResult:
        """Confirm a pending order and send it to MT5.

        Requires explicit owner confirmation (Hard Gate #5). After
        confirm_order() succeeds, sends the order directly to MT5 via
        MT5ExecutionAdapter.send_confirmed_order() and marks the
        confirmation as consumed (consumes rate limit).

        Args:
            confirmation_key: The key returned by submit_signal().
            token: Session token for authorization (owner role required).
            session_store: SessionStore for token validation.

        Returns:
            SubmissionResult with status "submitted" if broker accepted,
            or "rejected" if confirmation or submission failed.
        """
        # Step 1: Validate session (owner required)
        session = session_store.validate_token(token) if session_store else None
        if session is None:
            return SubmissionResult(
                status="rejected",
                reason="invalid or expired session",
            )
        if session.role != "owner":
            return SubmissionResult(
                status="rejected",
                reason=f"insufficient role: {session.role} - owner required to confirm orders",
            )

        # Step 2: Confirm the order (owner required)
        if not self.auth.is_order_confirmed(confirmation_key):
            confirm_result = self.auth.confirm_order(
                token, confirmation_key, session_store
            )
            if not confirm_result.allowed:
                return SubmissionResult(
                    status="rejected",
                    reason=confirm_result.reason or "confirmation failed",
                    evidence=confirm_result.evidence,
                )

        # Step 3: Retrieve the stored OrderRequest
        order_request = self._pending.pop(confirmation_key, None)

        # Step 3: Send to MT5 directly (no re-authorization)
        adapter_result = self.adapter.send_confirmed_order(
            order_request, confirmation_key
        )

        return SubmissionResult(
            status="submitted" if adapter_result.allowed else "rejected",
            reason=adapter_result.reason or "order sent",
            confirmation_key=confirmation_key,
            symbol=order_request.symbol,
            side=order_request.side,
            volume=str(order_request.volume),
            price=str(order_request.price) if order_request.price else None,
            stop_loss=str(order_request.stop_loss) if order_request.stop_loss else None,
            take_profit=str(order_request.take_profit) if order_request.take_profit else None,
            evidence=adapter_result.evidence,
        )

    def get_pending(self, confirmation_key: str) -> OrderRequest | None:
        """Retrieve a pending OrderRequest by confirmation key (read-only)."""
        return self._pending.get(confirmation_key)

    def clear_pending(self, confirmation_key: str) -> None:
        """Remove a pending order (e.g., after cancellation)."""
        self._pending.pop(confirmation_key, None)