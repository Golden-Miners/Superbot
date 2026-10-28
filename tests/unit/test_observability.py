"""Tests for structured logging with correlation IDs and secret redaction (M1.4).

Schema.md: secrets never logged. PRD §14: redact secrets from logs/exports.
No import-time network/MT5/database/model work.
"""

from __future__ import annotations

import logging

from superbot.observability.logging import (
    clear_correlation_id,
    configure_logging,
    get_correlation_id,
    get_logger,
    redact_secrets,
    set_correlation_id,
)


def test_correlation_id_lifecycle():
    assert get_correlation_id() is None
    cid = set_correlation_id("corr-123")
    assert cid == "corr-123"
    assert get_correlation_id() == "corr-123"
    clear_correlation_id()
    assert get_correlation_id() is None


def test_redact_secrets_masks_known_keys():
    masked = redact_secrets("MT5_PASSWORD=hunter2 api_key=abc123")
    assert "hunter2" not in masked
    assert "abc123" not in masked
    assert "MT5_PASSWORD=" in masked or "REDACTED" in masked


def test_logger_emits_json_with_correlation_id(caplog):
    configure_logging()
    set_correlation_id("corr-test-1")
    logger = get_logger("superbot.test")
    with caplog.at_level(logging.INFO, logger="superbot.test"):
        logger.info("sample event", extra={"instrument": "XAUUSD"})
    record = caplog.records[0]
    assert getattr(record, "correlation_id", None) == "corr-test-1"
    clear_correlation_id()
