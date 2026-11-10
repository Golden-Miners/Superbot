"""AI configuration for Superbot execution pipeline.

Loads AI model settings from YAML config and validates values.
Stdlib-only; no import-time network or model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class AIConfigError(ValueError):
    """Raised when AI configuration values fail validation."""


@dataclass
class AIConfig:
    """AI model configuration for signal generation.

    Args:
        model: Ollama model name (e.g. "llama3:8b").
        base_url: Ollama server URL (e.g. "http://localhost:11434").
        timeout_seconds: Request timeout in seconds (non-negative).
        confidence_threshold: Minimum confidence for signal acceptance (0.0-1.0).
    """

    model: str
    base_url: str
    timeout_seconds: int
    confidence_threshold: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model:
            raise AIConfigError("model is required")
        if not isinstance(self.base_url, str) or not self.base_url:
            raise AIConfigError("base_url is required")
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds < 0:
            raise AIConfigError("timeout_seconds must be a non-negative integer")
        if not isinstance(self.confidence_threshold, Decimal):
            try:
                self.confidence_threshold = Decimal(str(self.confidence_threshold))
            except (ValueError, TypeError) as exc:
                raise AIConfigError("confidence_threshold must be Decimal") from exc
        if self.confidence_threshold < Decimal("0") or self.confidence_threshold > Decimal("1"):
            raise AIConfigError("confidence_threshold must be between 0 and 1")
