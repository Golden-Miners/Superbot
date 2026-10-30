"""M9.7 — Prompt injection, untrusted text and malformed output tests.

Deterministic security validation service:
- PromptInjectionDetector: detects injection attempts (ignore previous, system override, role play)
- UntrustedTextSanitizer: strips HTML/script tags, shell metacharacters, SQL injection patterns
- MalformedOutputDetector: validates output against an expected schema (JSON, required fields, types)
- InputValidator: validates input length, null bytes, control characters
- SecurityResult: pass/fail with reasons
- Stdlib-only; no import-time network activity; no AI writes official state.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any

INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "ignore_previous_instructions"),
    (r"disregard\s+(all\s+)?previous\s+instructions", "disregard_previous_instructions"),
    (r"system\s*:\s*(reveal|override|ignore)", "system_override"),
    (r"you\s+are\s+now\s+(a\s+)?(developer|unrestricted|different)", "role_play_override"),
    (r"pretend\s+you\s+are", "role_play_override"),
    (r"jailbreak", "jailbreak_attempt"),
    (r"forget\s+(everything|all|your\s+instructions)", "forget_instructions"),
    (r"developer\s+mode", "developer_mode"),
]


HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
SHELL_META_PATTERN = re.compile(r"[;&|`$()<>!]")
SQL_PATTERNS: list[str] = [
    r"\b(select|insert|update|delete|drop|alter|create|exec|union)\b",
    r"--",
    r";\s*drop",
    r"\bor\s+1\s*=\s*1\b",
    r"\bdrop\s+table\b",
]


@dataclass(frozen=True)
class SecurityResult:
    """Result of a security check."""

    passed: bool
    reasons: list[str]


class PromptInjectionDetector:
    """Detects prompt injection attempts in user-supplied text."""

    def detect(self, text: str) -> SecurityResult:
        """Return SecurityResult indicating whether text contains injection patterns."""
        reasons: list[str] = []
        lowered = text.lower()
        for pattern, name in INJECTION_PATTERNS:
            if re.search(pattern, lowered):
                reasons.append(f"prompt injection pattern detected: {name}")
        return SecurityResult(passed=len(reasons) == 0, reasons=reasons)


class UntrustedTextSanitizer:
    """Sanitizes untrusted text by removing dangerous patterns."""

    def sanitize(self, text: str) -> str:
        """Return sanitized text with HTML tags, shell metacharacters, and SQL patterns removed."""
        sanitized = HTML_TAG_PATTERN.sub("", text)
        sanitized = SHELL_META_PATTERN.sub("", sanitized)
        for pattern in SQL_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
        # Unescape any HTML entities that could reconstruct tags
        sanitized = html.unescape(sanitized)
        # Strip any tags revealed after unescaping
        sanitized = HTML_TAG_PATTERN.sub("", sanitized)
        return sanitized.strip()


class MalformedOutputDetector:
    """Validates model output against an expected JSON schema."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema

    def detect(self, output: str) -> SecurityResult:
        """Return SecurityResult indicating whether output conforms to schema."""
        reasons: list[str] = []

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, ValueError) as exc:
            return SecurityResult(passed=False, reasons=[f"invalid JSON: {exc}"])

        if not isinstance(data, dict):
            return SecurityResult(passed=False, reasons=["output is not a JSON object"])

        required = self.schema.get("required", [])
        for field_name in required:
            if field_name not in data:
                reasons.append(f"missing required field: {field_name}")

        properties = self.schema.get("properties", {})
        for field_name, value in data.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    reasons.append(f"field {field_name} is not a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    reasons.append(f"field {field_name} is not a number")
                elif expected_type == "integer" and not isinstance(value, int):
                    reasons.append(f"field {field_name} is not an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    reasons.append(f"field {field_name} is not a boolean")

        return SecurityResult(passed=len(reasons) == 0, reasons=reasons)


class InputValidator:
    """Validates raw input against length and character constraints."""

    def __init__(self, max_length: int, allow_null_bytes: bool, allow_control_chars: bool) -> None:
        self.max_length = max_length
        self.allow_null_bytes = allow_null_bytes
        self.allow_control_chars = allow_control_chars

    def validate(self, text: str) -> SecurityResult:
        """Return SecurityResult indicating whether input is valid."""
        reasons: list[str] = []

        if len(text) > self.max_length:
            reasons.append(f"input length {len(text)} exceeds max {self.max_length}")

        if "\x00" in text and not self.allow_null_bytes:
            reasons.append("input contains null bytes")

        if not self.allow_control_chars:
            for ch in text:
                if ord(ch) < 32 and ch not in ("\t", "\n", "\r"):
                    reasons.append(f"input contains control character U+{ord(ch):04X}")
                    break

        return SecurityResult(passed=len(reasons) == 0, reasons=reasons)


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration shared across validation entry points."""

    max_input_length: int = 1000
    allow_null_bytes: bool = False
    allow_control_chars: bool = False


def detect_prompt_injection(text: str) -> SecurityResult:
    """Convenience: detect prompt injection in text."""
    return PromptInjectionDetector().detect(text)


def sanitize_untrusted_text(text: str) -> str:
    """Convenience: sanitize untrusted text."""
    return UntrustedTextSanitizer().sanitize(text)


def validate_input(
    text: str,
    max_length: int = 1000,
    allow_null_bytes: bool = False,
    allow_control_chars: bool = False,
) -> SecurityResult:
    """Convenience: validate input."""
    return InputValidator(
        max_length=max_length,
        allow_null_bytes=allow_null_bytes,
        allow_control_chars=allow_control_chars,
    ).validate(text)


def validate_output(output: str, schema: dict[str, Any]) -> SecurityResult:
    """Convenience: validate output against a schema."""
    return MalformedOutputDetector(schema).detect(output)
