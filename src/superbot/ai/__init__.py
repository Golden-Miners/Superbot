"""AI signal generation package (V2.9).

Wires AI/ML model-based signal generation to the MT5 execution pipeline
through ExecutionPermissionService. All safety gates remain in place:
READ_ONLY mode blocks writes, live-only demo server allowlist, rate
limiting, and operator confirmation before any order is sent to MT5.

Stdlib-only; no import-time network or model activity.
"""

from superbot.ai.ai_config import AIConfig, AIConfigError
from superbot.ai.ollama_client import OllamaClient, OllamaClientError
from superbot.ai.signal_generator import AISignalGenerator, AISignal

__all__ = [
    "AIConfig",
    "AIConfigError",
    "OllamaClient",
    "OllamaClientError",
    "AISignalGenerator",
    "AISignal",
]
