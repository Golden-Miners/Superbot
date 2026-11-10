"""AI signal to order request translation (V2.9).

Translates AISignal dataclass objects into OrderRequest objects
suitable for authorization via ExecutionPermissionService.

Stdlib-only; no import-time network or model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from superbot.ai.ai_config import AIConfig
from superbot.ai.signal_generator import AISignal
from superbot.m11.execution_authorizer import ExecutionPermissionService, OrderRequest
from superbot.m11.mt5_data_provider import MT5DataProvider


@dataclass(frozen=True)
class TranslationResult:
    """Result of translating an AISignal into an OrderRequest.

    Attributes:
        order_request: The resulting OrderRequest if translation succeeded.
        reason: Human-readable reason string (e.g. "translated", "insufficient confidence").
        evidence: Optional dict with metadata about the translation.
    """

    order_request: OrderRequest | None
    reason: str
    evidence: dict | None = None

    @property
    def allowed(self) -> bool:
        """Return True if the order request was created successfully."""
        return self.order_request is not None

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying OrderRequest when available."""
        if self.order_request is not None:
            return getattr(self.order_request, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )


class AIOrderTranslator:
    """Translates AI-generated signals into MT5 ExecutionPermissionService orders.

    Maps AI-signal fields to OrderRequest fields and validates against
    the authorization service before returning the OrderRequest.

    All symbols, sides, volumes, prices, stop-losses, take-profits come
    directly from the AISignal produced by the AI signal generator.
    """

    def __init__(
        self,
        auth: ExecutionPermissionService | None = None,
        mt5_data_provider: MT5DataProvider | None = None,
        config: AIConfig | None = None,
    ) -> None:
        self.auth = auth
        self.mt5_data_provider = mt5_data_provider
        self.config = config or AIConfig(
            model="llama3:8b",
            base_url="http://localhost:11434",
            timeout_seconds=15,
            confidence_threshold=Decimal("0.80"),
        )

    def translate(
        self,
        signal: AISignal,
        token: str | None = None,
        session_store=None,
    ) -> TranslationResult:
        """Translate an AISignal into an OrderRequest.

        Args:
            signal: The AISignal produced by the AI signal generator.
            token: Optional session token for authorization validation.
            session_store: Optional session store for token validation.

        Returns:
            TranslationResult containing the OrderRequest if translation
            succeeded, or reason if it failed.

        Raises:
            ValueError: If the signal is missing required fields.
        """
        # Validate required fields
        if not signal.symbol:
            return TranslationResult(
                order_request=None,
                reason="missing symbol",
                evidence={"signal": signal},
            )
        if signal.side not in ("buy", "sell"):
            return TranslationResult(
                order_request=None,
                reason=f"invalid side: {signal.side}",
                evidence={"signal": signal},
            )
        if not signal.volume or signal.volume <= Decimal("0"):
            return TranslationResult(
                order_request=None,
                reason=f"invalid volume: {signal.volume}",
                evidence={"signal": signal},
            )

        # Confidence threshold check
        if signal.confidence < self.config.confidence_threshold:
            return TranslationResult(
                order_request=None,
                reason=f"confidence {signal.confidence} below threshold {self.config.confidence_threshold}",
                evidence={
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "confidence": str(signal.confidence),
                    "threshold": str(self.config.confidence_threshold),
                },
            )

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

        return TranslationResult(
            order_request=order_request,
            reason="translated",
            evidence={
                "signal": signal,
                "symbol": signal.symbol,
                "side": signal.side,
                "confidence": str(signal.confidence),
                "reasoning": signal.reasoning,
                "model": signal.model,
            },
        )

    def translate_and_authorize(
        self,
        signal: AISignal,
        token: str | None,
        session_store,
    ) -> tuple[OrderRequest | None, str | None]:
        """Translate an AI signal and authorize it through ExecutionPermissionService.

        This is the full pipeline step: signal → OrderRequest → authorize.

        Args:
            signal: The AISignal produced by the AI signal generator.
            token: Session token for authorization.
            session_store: SessionStore for token validation.

        Returns:
            Tuple of (OrderRequest | None, reason str | None).
            If allowed is True, returns (OrderRequest, None).
            If rejected, returns (None, reason).
        """
        translation = self.translate(signal, token, session_store)

        if not translation.order_request:
            return None, translation.reason

        order_request = translation.order_request

        # Authorize through ExecutionPermissionService (all safety gates)
        if self.auth is None:
            return None, "no authorization service configured"

        auth_result = self.auth.authorize(
            order_request=order_request,
            token=token,
            session_store=session_store,
        )

        if not auth_result.allowed:
            return None, auth_result.reason or "authorization denied"

        return order_request, None
