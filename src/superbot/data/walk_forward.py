"""Walk-forward windows and metric accounting (schema.md section 6.2).

Generates >=3 walk-forward windows sliding chronologically across data:
train -> validation -> test with optional gap between val and test.
Provides deterministic metric accounting across windows and stability checks.

Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class WalkForwardError(ValueError):
    """Raised when walk-forward generation fails."""


class LeakageError(ValueError):
    """Raised when data leakage is detected across windows."""


@dataclass(frozen=True)
class WalkForwardSpec:
    """Versioned walk-forward specification."""

    schema_version: str
    spec_id: str
    n_windows: int
    train_bars: int
    val_bars: int
    test_bars: int
    gap_bars: int
    step_bars: int

    def __post_init__(self) -> None:
        if self.n_windows < 3:
            raise ValueError("n_windows must be >= 3")


@dataclass(frozen=True)
class WalkForwardWindow:
    """A single walk-forward window: train / validation / test timestamps."""

    window_id: str
    train_ts: list[int]
    val_ts: list[int]
    test_ts: list[int]
    gap_ts: list[int]


@dataclass(frozen=True)
class WindowMetrics:
    """Metrics for a single walk-forward window."""

    window_id: str
    pf: Decimal
    sharpe: Decimal
    sortino: Decimal
    max_dd_pct: Decimal
    trade_count: int


@dataclass(frozen=True)
class MetricAccountingResult:
    """Aggregated metric accounting across windows."""

    pf_mean: Decimal
    pf_std: Decimal
    sharpe_mean: Decimal
    sharpe_std: Decimal
    sortino_mean: Decimal
    sortino_std: Decimal
    max_dd_max: Decimal
    trade_count_total: int
    window_count: int


@dataclass(frozen=True)
class StabilityResult:
    """Stability check result across windows."""

    stable: bool
    pf_cv_pct: Decimal
    message: str


@dataclass
class MetricAccounting:
    """Accumulates per-window metrics for aggregate accounting."""

    def __init__(self) -> None:
        self._window_metrics: list[WindowMetrics] = []

    def add_window(
        self,
        window_id: str,
        pf: Decimal,
        sharpe: Decimal,
        sortino: Decimal,
        max_dd_pct: Decimal,
        trade_count: int,
    ) -> None:
        """Add metrics for one window."""
        self._window_metrics.append(
            WindowMetrics(
                window_id=window_id,
                pf=pf,
                sharpe=sharpe,
                sortino=sortino,
                max_dd_pct=max_dd_pct,
                trade_count=trade_count,
            )
        )

    def summary(self) -> MetricAccountingResult:
        """Compute aggregate metrics across all windows."""
        if not self._window_metrics:
            return MetricAccountingResult(
                pf_mean=Decimal(0),
                pf_std=Decimal(0),
                sharpe_mean=Decimal(0),
                sharpe_std=Decimal(0),
                sortino_mean=Decimal(0),
                sortino_std=Decimal(0),
                max_dd_max=Decimal(0),
                trade_count_total=0,
                window_count=0,
            )

        n = Decimal(len(self._window_metrics))
        pf_vals = [m.pf for m in self._window_metrics]
        sharpe_vals = [m.sharpe for m in self._window_metrics]
        sortino_vals = [m.sortino for m in self._window_metrics]
        max_dd_vals = [m.max_dd_pct for m in self._window_metrics]

        pf_mean = sum(pf_vals) / n
        sharpe_mean = sum(sharpe_vals) / n
        sortino_mean = sum(sortino_vals) / n
        max_dd_max = max(max_dd_vals)
        trade_count_total = sum(m.trade_count for m in self._window_metrics)

        def _std(vals: list[Decimal], mean: Decimal) -> Decimal:
            if len(vals) <= 1:
                return Decimal(0)
            var = sum((v - mean) ** 2 for v in vals) / Decimal(len(vals) - 1)
            return var.sqrt()

        pf_std = _std(pf_vals, pf_mean)
        sharpe_std = _std(sharpe_vals, sharpe_mean)
        sortino_std = _std(sortino_vals, sortino_mean)

        return MetricAccountingResult(
            pf_mean=pf_mean,
            pf_std=pf_std,
            sharpe_mean=sharpe_mean,
            sharpe_std=sharpe_std,
            sortino_mean=sortino_mean,
            sortino_std=sortino_std,
            max_dd_max=max_dd_max,
            trade_count_total=trade_count_total,
            window_count=len(self._window_metrics),
        )


def generate_windows(
    bars: list[int],
    spec: WalkForwardSpec,
) -> list[WalkForwardWindow]:
    """Generate walk-forward windows sliding chronologically across bars.

    Each window: train -> validation -> test with optional gap between val and test.
    Windows slide forward by step_bars. Requires at least 3 windows.

    Raises ValueError if insufficient bars or n_windows < 3.
    """
    if spec.n_windows < 3:
        raise ValueError("n_windows must be >= 3")

    if not bars:
        raise ValueError("bars must not be empty")

    (spec.train_bars + spec.val_bars + spec.test_bars + spec.gap_bars)
    windows: list[WalkForwardWindow] = []

    start = 0
    while len(windows) < spec.n_windows:
        needed = spec.train_bars + spec.val_bars + spec.test_bars + spec.gap_bars
        if start + needed > len(bars):
            break

        window_start = start
        train_ts = bars[window_start : window_start + spec.train_bars]
        val_start = window_start + spec.train_bars
        val_ts = bars[val_start : val_start + spec.val_bars]
        gap_start = val_start + spec.val_bars
        gap_ts = bars[gap_start : gap_start + spec.gap_bars]
        test_start = gap_start + spec.gap_bars
        test_ts = bars[test_start : test_start + spec.test_bars]

        windows.append(
            WalkForwardWindow(
                window_id=f"{spec.spec_id}_w{len(windows) + 1}",
                train_ts=train_ts,
                val_ts=val_ts,
                test_ts=test_ts,
                gap_ts=gap_ts,
            )
        )
        start += spec.step_bars

    if len(windows) < spec.n_windows:
        raise ValueError(
            f"insufficient bars for {spec.n_windows} windows; got {len(windows)} windows"
        )

    return windows


def check_stability(accounting: MetricAccounting) -> StabilityResult:
    """Check stability across windows: PF coefficient of variation < 10%."""
    summary = accounting.summary()
    if summary.window_count == 0:
        return StabilityResult(
            stable=False,
            pf_cv_pct=Decimal(0),
            message="no windows",
        )

    if summary.pf_mean == Decimal(0):
        return StabilityResult(
            stable=False,
            pf_cv_pct=Decimal(0),
            message="zero mean PF",
        )

    pf_cv_pct = (summary.pf_std / summary.pf_mean) * Decimal(100)
    stable = pf_cv_pct < Decimal(10)
    message = "stable" if stable else "high variance across windows"

    return StabilityResult(
        stable=stable,
        pf_cv_pct=pf_cv_pct,
        message=message,
    )
