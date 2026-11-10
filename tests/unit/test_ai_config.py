"""RED tests for V2.9 — AI Signal Generator (Phase 1: AI Infrastructure).

Covers:
- AIConfig loads from YAML config with model/base_url/timeout/threshold
- AIConfigError raised on invalid config values
- OllamaClient.generate() sends prompt to Ollama, returns parsed response
- OllamaClient handles connection errors, timeouts, malformed JSON
- AISignalGenerator.generate() builds prompt from market + account data
- AISignalGenerator returns AISignal with confidence >= threshold
- AISignalGenerator rejects signals below confidence threshold

No live trading authorized. Read-only market data only.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime

import pytest

from superbot.ai.ai_config import AIConfig, AIConfigError
from superbot.ai.ollama_client import OllamaClient, OllamaClientError
from superbot.ai.signal_generator import AISignalGenerator, AISignal


# --- RED tests for AIConfig ---


def test_ai_config_loads_from_dict():
    """AIConfig can be created from dict with valid values."""
    config = AIConfig(
        model="llama3:8b",
        base_url="http://localhost:11434",
        timeout_seconds=15,
        confidence_threshold=0.80,
    )
    assert config.model == "llama3:8b"
    assert config.base_url == "http://localhost:11434"
    assert config.timeout_seconds == 15
    assert config.confidence_threshold == Decimal("0.80")


def test_ai_config_rejects_invalid_confidence_threshold():
    """AIConfigError raised when confidence_threshold outside [0,1]."""
    with pytest.raises(AIConfigError, match="confidence_threshold"):
        AIConfig(
            model="llama3:8b",
            base_url="http://localhost:11434",
            timeout_seconds=15,
            confidence_threshold=Decimal("1.5"),
        )


def test_ai_config_rejects_negative_timeout():
    """AIConfigError raised when timeout_seconds is negative."""
    with pytest.raises(AIConfigError, match="timeout_seconds"):
        AIConfig(
            model="llama3:8b",
            base_url="http://localhost:11434",
            timeout_seconds=-1,
            confidence_threshold=Decimal("0.80"),
        )


# --- RED tests for OllamaClient ---


def test_ollama_client_creates():
    """OllamaClient can be instantiated."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=15)
    assert client is not None
    assert client.base_url == "http://localhost:11434"
    assert client.timeout_seconds == 15


def test_ollama_client_generate_returns_response():
    """generate() returns parsed JSON response from Ollama."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=15)

    # Mock successful response
    client._post = lambda url, json: {
        "response": '{"side": "buy", "volume": 0.01, "stop_loss": 4050.00}'
    }

    result = client.generate(prompt="test prompt")
    assert result is not None
    assert result["side"] == "buy"
    assert result["volume"] == 0.01
    assert result["stop_loss"] == 4050.00


def test_ollama_client_generate_raises_on_connection_error():
    """generate() raises OllamaClientError on connection error."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=15)

    client._post = lambda url, json: (_ for _ in ()).throw(
        ConnectionError("connection refused")
    )

    with pytest.raises(OllamaClientError, match="connection"):
        client.generate(prompt="test prompt")


def test_ollama_client_generate_raises_on_timeout():
    """generate() raises OllamaClientError on timeout."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=15)

    client._post = lambda url, json: (_ for _ in ()).throw(
        TimeoutError("request timed out")
    )

    with pytest.raises(OllamaClientError, match="timeout"):
        client.generate(prompt="test prompt")


def test_ollama_client_generate_raises_on_invalid_json():
    """generate() raises OllamaClientError on invalid JSON response."""
    client = OllamaClient(base_url="http://localhost:11434", timeout_seconds=15)

    client._post = lambda url, json: {"response": "not valid json"}

    with pytest.raises(OllamaClientError, match="invalid json"):
        client.generate(prompt="test prompt")


# --- RED tests for AISignalGenerator ---


def test_ai_signal_generator_creates():
    """AISignalGenerator can be instantiated."""
    provider = None  # Will use FakeMT5DataProvider
    auth = None
    translator = None
    generator = AISignalGenerator(
        mt5_data_provider=provider,
        order_translator=translator,
        auth=auth,
        config=None,
    )
    assert generator is not None


def test_ai_signal_generator_rejects_low_confidence():
    """generate() returns None when confidence below threshold."""
    pass  # Will implement after SignalTranslator exists


def test_ai_signal_generator_returns_signal_above_threshold():
    """generate() returns AISignal when confidence >= threshold."""
    pass  # Will implement after SignalTranslator exists


# --- AISignal dataclass tests ---


def test_ai_signal_creates():
    """AISignal can be created with all fields."""
    signal = AISignal(
        symbol="XAUUSD",
        side="buy",
        volume=Decimal("0.01"),
        price=Decimal("3875.75"),
        stop_loss=Decimal("3870.00"),
        take_profit=Decimal("3880.00"),
        confidence=Decimal("0.85"),
        reasoning="Bullish engulfing pattern on M5",
        model="llama3:8b",
        timestamp_utc=datetime.now(tz=UTC),
    )
    assert signal.symbol == "XAUUSD"
    assert signal.side == "buy"
    assert signal.confidence == Decimal("0.85")
