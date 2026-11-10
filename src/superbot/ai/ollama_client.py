"""Ollama HTTP client for AI signal generation (V2.9).

Wraps Ollama's /api/generate endpoint with timeout, retry, and JSON parsing.
Stdlib-only; no import-time network activity.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime


class OllamaClientError(ValueError):
    """Raised when Ollama communication fails (connection, timeout, bad JSON)."""


class OllamaClient:
    """Client for Ollama's /api/generate endpoint.

    Sends a prompt to a local Ollama server and parses the JSON response.
    Designed to fail closed: any communication error raises OllamaClientError
    so callers can degrade gracefully (e.g., skip AI signal and keep trading
    with deterministic rules only).
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout_seconds: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _post(self, url: str, data: bytes) -> dict:
        """Send a POST request to Ollama and return the parsed JSON response."""
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise OllamaClientError(f"connection error: {exc}") from exc
        except TimeoutError as exc:
            raise OllamaClientError("timeout") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"invalid JSON response: {exc}") from exc

    def generate(self, prompt: str) -> dict:
        """Send a prompt to Ollama and return the parsed JSON response.

        Args:
            prompt: Text prompt to send to the model.

        Returns:
            Parsed JSON dict from the model's ``response`` field.

        Raises:
            OllamaClientError: On connection error, timeout, or invalid JSON.
        """
        payload = {
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        try:
            response = self._post(f"{self.base_url}/api/generate", data)
        except TimeoutError as exc:
            raise OllamaClientError("timeout") from exc
        except Exception as exc:
            raise OllamaClientError(f"{exc}") from exc

        raw_text = response.get("response", "")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"invalid json: {exc}") from exc

    def extract_text(self, response: dict) -> str:
        """Extract the generated text from an Ollama response dict."""
        return response.get("response", "")
