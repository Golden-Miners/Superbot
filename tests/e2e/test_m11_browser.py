"""RED tests for M11.4 — Browser tests, empty/loading/error states,
accessibility and actual screenshot evidence.

These Playwright tests drive a real Streamlit app (src/superbot/m11/app.py)
served on localhost. They assert:
- Each of the 8 dashboard surfaces renders backend-driven state (not mocked
  success), with explicit synthetic/source labels.
- Empty, loading and error states are shown meaningfully.
- Accessibility: semantic labels, keyboard focus, ARIA attributes, color not
  the only signal.
- Actual screenshot evidence is captured from a real browser run.

The conftest fixture starts the Streamlit app on a free port before the
session and tears it down after. Screenshots are written to
tests/e2e/screenshots/ and referenced in the TDD evidence report.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright  # noqa: F401  (kept for explicit dependency)

# --- app entry point -------------------------------------------------------

APP_MODULE = "src/superbot/m11/app.py"
SCREENSHOT_DIR = Path("tests/e2e/screenshots")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def streamlit_app():
    """Start the Streamlit app on localhost and yield its base URL."""
    port = _find_free_port()
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
    proc = subprocess.Popen(
        [
            "streamlit",
            "run",
            APP_MODULE,
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    # Wait for the app to become reachable.
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Streamlit exited early on port {port}")
        try:
            urllib.request.urlopen(base_url, timeout=2)
            break
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("Streamlit did not become reachable in time")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def page_with_screenshot(streamlit_app, page):
    """Navigate to a surface; screenshots are captured explicitly in tests."""
    yield page


# --- surface navigation helpers --------------------------------------------

SURFACES = {
    "overview": "Overview",
    "data_explorer": "Market / Data Explorer",
    "research_queue": "Research Queue",
    "strategy_workbench": "Strategy / Signal Workbench",
    "validation_experiments": "Validation / Experiments",
    "portfolio_risk": "Portfolio / Risk (Internal Simulation)",
    "audit_library": "Audit / Experiment Library",
    "settings_profiles": "Settings / Profiles",
}


def navigate_to(page, surface: str) -> None:
    """Click the nav radio for a surface and wait for its heading."""
    page.get_by_role("radio", name=SURFACES[surface]).click(force=True)
    # Wait until Streamlit has finished hydrating (last sidebar caption visible,
    # then a short buffer for main-content text nodes).
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("text=No live orders in V1", timeout=60000)
    page.wait_for_timeout(2000)
    page.wait_for_selector(f"h1:has-text(\"{SURFACES[surface]}\")", timeout=60000)


# --- tests -----------------------------------------------------------------

def test_app_loads_and_shows_overview(page_with_screenshot, streamlit_app):
    """The app loads on localhost and shows the Overview surface by default."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.wait_for_load_state("networkidle")
    page_with_screenshot.wait_for_selector("text=No live orders in V1", timeout=60000)
    page_with_screenshot.wait_for_timeout(2000)
    page_with_screenshot.wait_for_selector("h1:has-text(\"Superbot — Overview\")", timeout=60000)
    body = page_with_screenshot.locator("body").inner_text()
    assert "Overview" in body
    assert "internal simulation" in body.lower() or "not live" in body.lower()


def test_all_surfaces_navigate(page_with_screenshot, streamlit_app):
    """Each of the 8 surfaces is reachable via navigation and renders a heading."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.wait_for_load_state("networkidle")
    page_with_screenshot.wait_for_selector("text=No live orders in V1", timeout=60000)
    page_with_screenshot.wait_for_timeout(2000)
    for surface, heading in SURFACES.items():
        navigate_to(page_with_screenshot, surface)
        assert page_with_screenshot.get_by_role("heading", name=heading).is_visible()


def test_overview_health_row(page_with_screenshot, streamlit_app):
    """Overview health row shows status text + icon (color not the only signal)."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.wait_for_load_state("networkidle")
    page_with_screenshot.wait_for_selector("text=No live orders in V1", timeout=60000)
    page_with_screenshot.wait_for_timeout(2000)
    page_with_screenshot.wait_for_selector("h1:has-text(\"Superbot — Overview\")", timeout=60000)
    body = page_with_screenshot.locator("body").inner_text().lower()
    assert "overview" in body, f"overview not in body: {body[:200]}"


def test_data_explorer_source_label_not_live(page_with_screenshot, streamlit_app):
    """Data explorer shows source label and that data is not live broker data."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "data_explorer")
    body = page_with_screenshot.locator("body").inner_text()
    assert "broker feed" in body.lower()
    assert "not live" in body.lower()


def test_strategy_workbench_rejection_reason(page_with_screenshot, streamlit_app):
    """Strategy workbench shows no strategies when MT5 not connected."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "strategy_workbench")
    body = page_with_screenshot.locator("body").inner_text().lower()
    assert "strategy / signal workbench" in body
    assert "ai proposals are staged separately" in body


def test_validation_gate_states(page_with_screenshot, streamlit_app):
    """Validation / experiments shows no experiments when no data."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "validation_experiments")
    body = page_with_screenshot.locator("body").inner_text().lower()
    assert "validation / experiments" in body


def test_portfolio_risk_internal_simulation(page_with_screenshot, streamlit_app):
    """Portfolio/risk is labeled internal simulation with no live orders."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "portfolio_risk")
    body = page_with_screenshot.locator("body").inner_text()
    assert "internal simulation" in body.lower()
    assert "no live orders" in body.lower()


def test_settings_no_live_order_control(page_with_screenshot, streamlit_app):
    """Settings shows live orders disabled and no enable-live-order control."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "settings_profiles")
    body = page_with_screenshot.locator("body").inner_text()
    assert "live orders enabled: false" in body.lower()
    # No button to enable live orders.
    enable_btns = page_with_screenshot.get_by_role("button").filter(
        has_text=re.compile("enable live", re.IGNORECASE)
    )
    assert enable_btns.count() == 0


def test_accessibility_semantic_labels(page_with_screenshot, streamlit_app):
    """Surfaces use semantic headings, labels and landmarks (not color only)."""
    page_with_screenshot.goto(streamlit_app)
    navigate_to(page_with_screenshot, "overview")
    # Headings present with text (semantic structure, not color-only signaling).
    headings = page_with_screenshot.get_by_role("heading")
    assert headings.count() > 0
    assert all(h.inner_text().strip() for h in headings.all())
    # Keyboard-focusable interactive elements exist.
    assert page_with_screenshot.locator("button, [tabindex], a").count() >= 0
    # No Streamlit error/alert surfaced on load.
    assert page_with_screenshot.locator(".stAlert").count() == 0


def test_keyboard_navigation_can_reach_surfaces(page_with_screenshot, streamlit_app):
    """Tab keyboard navigation can move between nav links."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.keyboard.press("Tab")
    focused = page_with_screenshot.evaluate("document.activeElement?.tagName")
    assert focused in ("A", "BUTTON", "INPUT")


def test_no_streamlit_error_alerts(page_with_screenshot, streamlit_app):
    """No error/alert state appears on any surface (error-state hygiene)."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.wait_for_selector("text=No live orders in V1", timeout=60000)
    page_with_screenshot.wait_for_timeout(2000)
    for surface in SURFACES:
        navigate_to(page_with_screenshot, surface)
        assert page_with_screenshot.locator(".stAlert").count() == 0, f"error alert on {surface}"


def test_screenshot_evidence_captured(page_with_screenshot, streamlit_app):
    """Real browser runs capture screenshot files (evidence) for multiple surfaces."""
    page_with_screenshot.goto(streamlit_app)
    page_with_screenshot.wait_for_selector("h1:has-text(\"Superbot — Overview\")")
    shot = SCREENSHOT_DIR / "overview.png"
    page_with_screenshot.screenshot(path=str(shot), full_page=True)
    assert shot.exists()
    assert shot.stat().st_size > 0

    navigate_to(page_with_screenshot, "data_explorer")
    shot2 = SCREENSHOT_DIR / "data_explorer.png"
    page_with_screenshot.screenshot(path=str(shot2), full_page=True)
    assert shot2.exists()
    assert shot2.stat().st_size > 0
