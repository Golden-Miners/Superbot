"""Structured logging with correlation IDs and secret redaction.

- Correlation IDs flow through a contextvar so every log record in a run
  carries the same request/job identifier.
- Secrets (passwords, tokens, API keys, broker credentials) are redacted from
  log messages; secret values are never written to logs.
- JSON output for machine parsing; safe for local files only.
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Keys whose values must never appear in logs. Extended only by decision.
_SECRET_KEYS = (
    "mt5_login",
    "mt5_password",
    "mt5_server",
    "mt5_token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
    "credential",
)


class InvalidObservabilityError(ValueError):
    """Raised when observability configuration is invalid."""


def set_correlation_id(correlation_id: str) -> str:
    """Bind a correlation ID to the current context. Returns the ID."""
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current context, or None."""
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)


class CorrelationFilter(logging.Filter):
    """Injects the current correlation ID into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Emits one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with JSON formatting and correlation injection.

    Idempotent: removes any previously added Superbot handler to avoid
    duplicate output on reconfiguration.
    """
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not getattr(h, "_superbot_handler", False)]
    handler = logging.StreamHandler()
    handler._superbot_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationFilter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a stdlib logger for the given name."""
    return logging.getLogger(name)


def redact_secrets(message: str) -> str:
    """Redact values associated with known secret keys in *message*."""
    result = message
    for key in _SECRET_KEYS:
        pattern = re.compile(r"(" + re.escape(key) + r")\s*[:=]\s*[^\s,}]+", re.IGNORECASE)
        result = pattern.sub(lambda m: m.group(1) + "=REDACTED", result)
    return result
