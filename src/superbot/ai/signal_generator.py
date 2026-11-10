"""AI signal generator for Superbot (V2.9).

Wraps Ollama LLM to generate trading signals from market + account data.
All signals route through ExecutionPermissionService for authorization;
no broker writes occur without explicit authorization chain.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from superbot.ai.ai_config import AIConfig
from superbot.ai.ollama_client import OllamaClient, OllamaClientError


class AISignalError(ValueError):
    """Raised when AI signal generation fails."""


@dataclass(frozen=True)
class AISignal:
    """An AI-generated trading signal, awaiting authorization.

    Not an order itself - must pass through ExecutionPermissionService
    before any broker write occurs.
    """

    symbol: str
    side: str  # "buy" or "sell"
    volume: Decimal
    price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    confidence: Decimal  # 0.0 to 1.0
    reasoning: str
    model: str
    timestamp_utc: datetime


class AISignalGenerator:
    """Generates trading signals via Ollama LLM.

    Builds a prompt from market data + account context, sends to Ollama,
    parses the JSON response into an AISignal, and applies confidence
    threshold gating. Returns None (no signal) when confidence is below
    threshold or when Ollama is unavailable - fail closed.
    """

    def __init__(
        self,
        mt5_data_provider=None,
        order_translator=None,
        auth=None,
        config: AIConfig | None = None,
    ) -> None:
        self.mt5_data_provider = mt5_data_provider
        self.order_translator = order_translator
        self.auth = auth
        self.config = config or AIConfig(
            model="llama3:8b",
            base_url="http://localhost:11434",
            timeout_seconds=15,
            confidence_threshold=Decimal("0.80"),
        )
        self.ollama = OllamaClient(
            base_url=self.config.base_url,
            timeout_seconds=self.config.timeout_seconds,
        )

    def generate(
        self,
        symbol: str,
        bars: list[dict],
        account_info: dict | None = None,
        positions: list[dict] | None = None,
    ) -> AISignal | None:
        """Generate a trading signal from market data.

        Args:
            symbol: Canonical symbol (e.g. "XAUUSD").
            bars: List of OHLCV bar dicts (most recent first).
            account_info: Optional account info dict (login, server, balance, equity).
            positions: Optional list of open position dicts.

        Returns:
            AISignal if confidence >= threshold, None otherwise.
            Returns None if Ollama is unavailable (fail closed).
        """
        prompt = self._build_prompt(symbol, bars, account_info, positions)

        try:
            response = self.ollama.generate(prompt)
        except OllamaClientError:
            # Fail closed: no AI signal when Ollama is unavailable
            return None

        text = self.ollama.extract_text(response)
        parsed = self._parse_response(text)
        if parsed is None:
            return None

        confidence = Decimal(str(parsed.get("confidence", 0)))
        if confidence < self.config.confidence_threshold:
            return None  # Below threshold - fail closed

        return AISignal(
            symbol=parsed.get("symbol", symbol),
            side=parsed.get("side", "buy"),
            volume=Decimal(str(parsed.get("volume", self.config.default_volume if hasattr(self.config, "default_volume") else "0.01"))),
            price=Decimal(str(parsed["entry_price"])) if parsed.get("entry_price") else None,
            stop_loss=Decimal(str(parsed["stop_loss"])) if parsed.get("stop_loss") else None,
            take_profit=Decimal(str(parsed["take_profit"])) if parsed.get("take_profit") else None,
            confidence=confidence,
            reasoning=parsed.get("reasoning", ""),
            model=self.config.model,
            timestamp_utc=datetime.now(tz=UTC),
        )

    def _build_prompt(
        self,
        symbol: str,
        bars: list[dict],
        account_info: dict | None = None,
        positions: list[dict] | None = None,
    ) -> str:
        """Build a prompt asking Ollama for a trading signal decision.

        Returns a JSON-only response format so parsing is deterministic.
        """
        # Build recent price context (last 5 bars)
        recent = bars[:5] if len(bars) >= 5 else bars
        price_history = []
        for bar in recent:
            price_history.append(
                f"  {bar.get('bar_open_utc', bar.get('t', '?'))}: "
                f"O={bar.get('open', bar.get('o', '?'))}, "
                f"H={bar.get('high', bar.get('h', '?'))}, "
                f"L={bar.get('low', bar.get('l', '?'))}, "
                f"C={bar.get('close', bar.get('c', '?'))}, "
                f"V={bar.get('volume', bar.get('v', '?'))}"
            )

        prompt = f"""You are a trading signal generator. Analyze the following market data for {symbol} and output a JSON object ONLY (no markdown, no explanation).

Recent OHLCV bars (most recent first):
{chr(10).join(price_history)}

Account info: {account_info or "not available"}
Open positions: {positions or []}

Respond with a JSON object containing exactly these fields:
- "side": "buy" or "sell" (or "hold" if no clear signal)
- "volume": decimal (order size in lots, e.g. 0.01)
- "entry_price": decimal or null
- "stop_loss": decimal or null
- "take_profit": decimal or null
- "confidence": decimal between 0.0 and 1.0
- "reasoning": short text explanation

Example:
{{"side": "buy", "volume": 0.01, "entry_price": 3875.75, "stop_loss": 3870.00, "take_profit": 3880.00, "confidence": 0.85, "reasoning": "Bullish engulfing pattern with volume confirmation"}}

Output ONLY the JSON object, nothing else."""

        return prompt

    def _parse_response(self, text: str) -> dict | None:
        """Parse JSON from Ollama response text.

        Returns dict or None if parsing fails.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from within text (in case Ollama wraps it)
            import re

            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            return None
