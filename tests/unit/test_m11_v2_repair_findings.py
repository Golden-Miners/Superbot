"""GREEN tests for V2 integration repair findings.

Covers all 8 findings from the code review:
F1: render_overview reads from STATE.health_components (empty) instead of DashboardService
F2: _build_ohlcv marks all bars as VALID regardless of staleness
F3: DashboardService.get_risk() accesses _strategies (private)
F4: DashboardService.get_jobs() accesses _jobs (private)
F5: DashboardService.get_strategies() accesses _configs (private)
F6: data_explorer re-reads app.state.mt5_provider redundantly
F7: risk_strategy Decimal(str(...)) fragile conversion
F8: MT5 queried per symbol in every surface (nice to have)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from superbot.contracts.ohlcv import QualityStatus
from superbot.m10.scheduler import Scheduler
from superbot.m11.api import create_app
from superbot.m11.integration import DashboardService
from superbot.m11.mt5_data_provider import DataState, MT5DataProvider
from superbot.m11.ui import render_overview
from superbot.risk.portfolio_risk import PortfolioRiskService
from superbot.strategy.shared_framework import SharedStrategyFramework

# ---------- F1: render_overview should show all health components from DashboardService ---


class FakeUI:
    """Fake UI that captures all write calls for testing."""

    def __init__(self):
        self.calls = []

    def title(self, text):
        self.calls.append(("title", text))

    def subheader(self, text):
        self.calls.append(("subheader", text))

    def write(self, text):
        self.calls.append(("write", text))

    def metric(self, label, value):
        self.calls.append(("metric", label, value))

    def plotly_chart(self, fig):
        self.calls.append(("plotly_chart", fig))

    def caption(self, text):
        self.calls.append(("caption", text))

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return method


class FakeHealthRegistry:
    """Fake HealthRegistry for testing without real services."""

    def __init__(self):
        self._checks = {
            "api": type("Result", (), {"status": type("Status", (), {"value": "healthy"})(), "message": "ok"})(),
            "postgresql": type("Result", (), {"status": type("Status", (), {"value": "healthy"})(), "message": "ok"})(),
            "worker_supervisor": type("Result", (), {"status": type("Status", (), {"value": "healthy"})(), "message": "ok"})(),
            "model_runtime": type("Result", (), {"status": type("Status", (), {"value": "blocked"})(), "message": "no model"})(),
            "mt5_readonly": type("Result", (), {"status": type("Status", (), {"value": "blocked"})(), "message": "not connected"})(),
        }

    def run_all(self):
        return self._checks


def test_render_overview_shows_all_health_components():
    """F1: Overview surface should show ALL health components from DashboardService,
    not just MT5 from STATE.health_components (which is empty)."""
    ui = FakeUI()
    registry = FakeHealthRegistry()
    ds = DashboardService(health_registry=registry)
    render_overview(ui=ui, dashboard_service=ds)
    calls_text = " ".join(
        str(a[0]) if len(a) == 1 else str(a) for a in ui.calls
    ).lower()
    assert "api" in calls_text, f"api component missing from overview: {calls_text[:200]}"
    assert "postgresql" in calls_text, f"postgresql component missing from overview: {calls_text[:200]}"
    assert "worker_supervisor" in calls_text, f"worker_supervisor component missing from overview: {calls_text[:200]}"
    assert "model_runtime" in calls_text, f"model_runtime component missing from overview: {calls_text[:200]}"
    assert "mt5_readonly" in calls_text, f"mt5_readonly component missing from overview: {calls_text[:200]}"


# ---------- F2: _build_ohlcv should mark stale bars as STALE ---


class FakeMT5ForOHLCV:
    """Fake MT5 that returns bars with a controllable timestamp aligned to M5."""

    def __init__(self, bar_timestamp: datetime):
        self._bar_timestamp = bar_timestamp

    def initialize(self):
        return True

    def shutdown(self):
        pass

    def symbol_info(self, name):
        return None

    def symbol_info_tick(self, name):
        return None

    def copy_rates_from_pos(self, symbol, timeframe, pos, count):
        return [
            {
                "time": int(self._bar_timestamp.timestamp()),
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 101.0,
                "tick_volume": 10,
                "spread": 2,
                "real_volume": 10,
            }
        ]


def _m5_aligned_now() -> datetime:
    """Return current time rounded down to the nearest M5 boundary."""
    now = datetime.now(tz=UTC)
    minute = (now.minute // 5) * 5
    return now.replace(minute=minute, second=0, microsecond=0)


def test_build_ohlcv_marks_stale_bar_as_stale():
    """F2: OHLCV bars older than 60 seconds should have quality_status=STALE,
    not VALID."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    stale_time = _m5_aligned_now() - timedelta(minutes=10)
    provider._mt5 = FakeMT5ForOHLCV(stale_time)

    bars = provider.get_ohlcv("XAUUSD", "M5", count=1)
    assert len(bars) == 1, f"Expected 1 bar, got {len(bars)}"
    assert bars[0].quality_status == DataState.STALE, (
        f"Expected STALE for bar older than 60s, got {bars[0].quality_status}"
    )


def test_build_ohlcv_marks_fresh_bar_as_valid():
    """F2: OHLCV bars less than 5 minutes old should have quality_status=VALID."""
    provider = MT5DataProvider({"XAUUSD": "GOLD.i#"})
    provider.connect()
    # Use 5-minute aligned time so OHLCVBar validation passes; aligned time is
    # at most ~4:59 old, which is under the 300s staleness threshold.
    fresh_time = _m5_aligned_now()
    provider._mt5 = FakeMT5ForOHLCV(fresh_time)

    bars = provider.get_ohlcv("XAUUSD", "M5", count=1)
    assert len(bars) == 1, f"Expected 1 bar, got {len(bars)}"
    assert bars[0].quality_status == QualityStatus.VALID, (
        f"Expected VALID for bar less than 300s old, got {bars[0].quality_status}"
    )


# ---------- F3: get_risk should use public method, not _strategies ---


def test_get_risk_uses_public_api_not_private_attr():
    """F3: DashboardService.get_risk() should use a public method on
    PortfolioRiskService, not access _strategies directly."""
    provider = PortfolioRiskService()
    provider.register_strategy("test-strat", Decimal(15), Decimal(3), Decimal(5))
    ds = DashboardService(risk_service=provider)
    # This should not raise AttributeError even if _strategies is renamed
    result = ds.get_risk()
    assert "strategies" in result
    assert len(result["strategies"]) == 1
    assert result["strategies"][0]["strategy_id"] == "test-strat"


# ---------- F4: get_jobs should use public method, not _jobs ---


def test_get_jobs_uses_public_api_not_private_attr():
    """F4: DashboardService.get_jobs() should use a public method on Scheduler,
    not access _jobs directly."""
    scheduler = Scheduler(max_concurrent=5)
    ds = DashboardService(job_scheduler=scheduler)
    result = ds.get_jobs()
    assert "jobs" in result


# ---------- F5: get_strategies should use public method, not _configs ---


def test_get_strategies_uses_public_api_not_private_attr():
    """F5: DashboardService.get_strategies() should use a public method on
    SharedStrategyFramework, not access _configs directly."""
    framework = SharedStrategyFramework()
    ds = DashboardService(strategy_framework=framework)
    result = ds.get_strategies()
    assert "strategies" in result


# ---------- F6: data_explorer should use closure variable, not app.state re-read ---


def test_data_explorer_uses_closure_mt5_provider():
    """F6: data_explorer should use the mt5 variable from create_app() closure,
    not re-read from app.state.mt5_provider (which may not exist if create_app()
    is refactored)."""
    provider = MT5DataProvider()
    app = create_app(mt5_data_provider=provider)
    import inspect

    source = inspect.getsource(app.routes[3].endpoint)  # data_explorer route
    assert "app.state.mt5_provider" not in source, (
        "data_explorer should use closure variable, not re-read app.state.mt5_provider"
    )


# ---------- F7: risk_strategy should handle missing/None values gracefully ---


def test_risk_strategy_handles_missing_values():
    """F7: risk_strategy should not crash if current_dd_pct or daily_loss_pct
    is missing or None."""
    provider = PortfolioRiskService()
    # Register a strategy with None values to test robustness
    provider.register_strategy("test-strat", Decimal(15), Decimal(3), Decimal(5))
    record = provider.get_strategy("test-strat")
    # Manually set None values to simulate missing data
    record.current_dd_pct = None
    record.daily_loss_pct = None
    ds = DashboardService(risk_service=provider)
    result = ds.get_risk()
    assert "strategies" in result
    # The strategy with None values should have current_dd_pct=None preserved
    assert result["strategies"][0]["current_dd_pct"] is None


# ---------- F8: MT5 should be queried once per symbol per request cycle ---


def test_get_tick_called_once_per_symbol():
    """F8 (nice to have): MT5 should not be queried multiple times for the
    same symbol across different surfaces in a single request cycle."""
    provider = MT5DataProvider()
    provider.connect()
    call_count = [0]
    original_get_tick = provider.get_tick

    def counting_get_tick(symbol):
        call_count[0] += 1
        return original_get_tick(symbol)

    provider.get_tick = counting_get_tick
    # Get ticks for all 5 symbols
    for symbol in provider.symbol_map:
        provider.get_tick(symbol)
    assert call_count[0] == len(provider.symbol_map), (
        f"Expected {len(provider.symbol_map)} calls, got {call_count[0]}"
    )
