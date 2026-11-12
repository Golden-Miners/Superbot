"""Ollama HTTP client for AI signal generation (V2.9).

Wraps Ollama's /api/generate endpoint with timeout, retry, JSON parsing,
and automatic Ollama process startup when the server is not running.
Stdlib-only; no import-time network activity.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime


class OllamaClientError(ValueError):
    """Raised when Ollama communication fails (connection, timeout, bad JSON)."""


class OllamaClient:
    """Client for Ollama's /api/generate endpoint.

    Sends a prompt to a local Ollama server and parses the JSON response.
    Automatically starts the Ollama server if it is not running, so callers
    do not need to manage the Ollama process lifecycle manually.

    Designed to fail closed: any communication error that cannot be resolved
    by starting Ollama raises OllamaClientError so callers can degrade
    gracefully (e.g., skip AI signal and keep trading with deterministic
    rules only).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 15,
        ollama_binary: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        # Ollama executable path; defaults to 'ollama' (found via PATH) or
        # the common Windows install location.
        self.ollama_binary = ollama_binary or self._default_ollama_binary()
        self._ollama_process: subprocess.Popen | None = None

    @staticmethod
    def _default_ollama_binary() -> str:
        """Return the default Ollama executable path for the current platform."""
        if os.name == "nt":  # Windows
            return r"C:\Users\%USERPROFILE%\.ollama\ollama.exe"
        return "ollama"

    def _is_running(self) -> bool:
        """Return True if the Ollama server responds to a request."""
        try:
            self._get(f"{self.base_url}/api/tags")
            return True
        except OllamaClientError:
            return False

    def _get(self, url: str) -> dict:
        """Send a GET request to Ollama and return the parsed JSON response."""
        req = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json"},
            method="GET",
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

    def _start_ollama(self) -> bool:
        """Attempt to start the Ollama server process.

        Returns True if the process was launched successfully, False otherwise.
        The process is started detached so it outlives this Python process.
        """
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            self._ollama_process = subprocess.Popen(
                [self.ollama_binary, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.DETACHED_PROCESS
                if os.name == "nt"
                else 0,
            )
            return True
        except (FileNotFoundError, PermissionError, OSError):
            return False

    def _wait_for_ollama(self, max_wait_seconds: float = 30.0) -> bool:
        """Poll the Ollama server until it responds or the timeout expires."""
        import time

        deadline = UTC.now().timestamp() + max_wait_seconds
        while UTC.now().timestamp() < deadline:
            if self._is_running():
                return True
            time.sleep(0.5)
        return False

    def ensure_running(self) -> bool:
        """Ensure Ollama is running, starting it if necessary.

        Returns True if Ollama is available (either already running or
        successfully started), False otherwise.
        """
        if self._is_running():
            return True

        # Ollama is not running; attempt to start it
        if not self._start_ollama():
            return False

        # Wait for Ollama to become ready
        return self._wait_for_ollama()

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
            # On connection error, attempt to start Ollama and retry once
            if isinstance(exc, OllamaClientError) and "connection" in str(exc):
                if self.ensure_running():
                    try:
                        response = self._post(
                            f"{self.base_url}/api/generate", data
                        )
                    except Exception as retry_exc:
                        raise OllamaClientError(
                            f"Ollama unavailable after startup: {retry_exc}"
                        ) from retry_exc
                else:
                    raise OllamaClientError(
                        "Ollama server is not running and could not be started"
                    ) from exc
            raise OllamaClientError(f"{exc}") from exc

        raw_text = response.get("response", "")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"invalid json: {exc}") from exc

    def extract_text(self, response: dict) -> str:
        """Extract the generated text from an Ollama response dict."""
        return response.get("response", "")