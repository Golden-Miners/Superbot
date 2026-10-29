"""ATR-relative volatility and hard blocks; thresholds OPEN, never guessed (schema.md section 7.5).

Deterministic ATR-relative volatility and hard-block service:
- ATR-relative volatility = ATR / current_price * 100
- Volatility block: pause trading when ATR-relative volatility exceeds configured threshold
- Hard blocks: pause trading when any configured hard-limit metric is breached
- All thresholds are OPEN configuration inputs; never hardcoded or guessed
- Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ATRReading:
    """ATR-relative volatility reading."""

    atr: Decimal
    current_price: Decimal
    atr_relative_volatility_pct: Decimal


@dataclass(frozen=True)
class VolatilityBlockResult:
    """Volatility block result."""

    blocked: bool
    atr_relative_volatility_pct: Decimal
    threshold_pct: Decimal
    reasons: list[str]


# VolatilityBlock is an alias for VolatilityBlockResult, kept for API compatibility.
VolatilityBlock = VolatilityBlockResult


@dataclass(frozen=True)
class HardBlock:
    """A single hard-block metric with its threshold."""

    metric_name: str
    threshold_pct: Decimal
    breached: bool = False


@dataclass(frozen=True)
class HardBlockResult:
    """Hard block check result."""

    blocked: bool
    breached_metrics: list[str]
    reasons: list[str]
    breached: bool = False


class ATRVolatilityService:
    """Computes ATR-relative volatility and volatility blocks."""

    def __init__(
        self,
        volatility_threshold_pct: Decimal,
    ) -> None:
        self.volatility_threshold_pct = volatility_threshold_pct

    def compute_reading(
        self,
        atr: Decimal,
        current_price: Decimal,
    ) -> ATRReading:
        """Compute ATRReading from ATR and current price."""
        if current_price == Decimal(0):
            atr_relative_volatility_pct = Decimal(0)
        else:
            atr_relative_volatility_pct = atr / current_price * Decimal(100)
        return ATRReading(
            atr=atr,
            current_price=current_price,
            atr_relative_volatility_pct=atr_relative_volatility_pct,
        )


class HardBlockService:
    """Manages hard-block metrics and checks them against current values."""

    def __init__(
        self,
    ) -> None:
        self._blocks: dict[str, HardBlock] = {}

    def add_hard_block(
        self,
        metric_name: str,
        threshold_pct: Decimal,
    ) -> None:
        """Add a hard-block metric with its threshold (OPEN configuration)."""
        self._blocks[metric_name] = HardBlock(
            metric_name=metric_name,
            threshold_pct=threshold_pct,
        )

    def get_hard_block(
        self,
        metric_name: str,
    ) -> HardBlock | None:
        """Get a hard block by metric name."""
        return self._blocks.get(metric_name)

    def check_hard_blocks(
        self,
        current_values: dict[str, Decimal],
    ) -> HardBlockResult:
        """Check all hard blocks against current values.

        Args:
            current_values: dict of metric_name -> current value

        Returns HardBlockResult with blocked flag and breached metric names.
        """
        breached: list[str] = []
        reasons: list[str] = []
        for name, block in self._blocks.items():
            current = current_values.get(name, Decimal(0))
            if current > block.threshold_pct:
                breached.append(name)
                reasons.append(f"{name} {current} exceeds threshold {block.threshold_pct}")
        blocked = len(breached) > 0
        return HardBlockResult(
            blocked=blocked,
            breached=blocked,
            breached_metrics=breached,
            reasons=reasons,
        )


def compute_atr(
    candles: list[dict],
) -> Decimal:
    """Compute Average True Range from candle data.

    Each candle dict has keys: high, low, close, prev_close.
    TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    ATR = mean of TR values.
    """
    if not candles:
        return Decimal(0)
    trs: list[Decimal] = []
    for c in candles:
        high = Decimal(str(c["high"]))
        low = Decimal(str(c["low"]))
        Decimal(str(c["close"]))
        prev_close = Decimal(str(c["prev_close"]))
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        trs.append(max(tr1, tr2, tr3))
    return sum(trs) / Decimal(len(trs))


def compute_atr_relative_volatility(
    atr: Decimal,
    current_price: Decimal,
) -> Decimal:
    """Compute ATR-relative volatility % = ATR / current_price * 100."""
    if current_price == Decimal(0):
        return Decimal(0)
    return atr / current_price * Decimal(100)


def compute_volatility_block(
    atr_relative_volatility_pct: Decimal,
    threshold_pct: Decimal,
) -> VolatilityBlockResult:
    """Check ATR-relative volatility against threshold.

    Returns VolatilityBlockResult with blocked=True when vol > threshold.
    """
    reasons: list[str] = []
    blocked = atr_relative_volatility_pct > threshold_pct
    if blocked:
        reasons.append(
            f"atr_relative_volatility {atr_relative_volatility_pct} exceeds threshold {threshold_pct}"
        )
    return VolatilityBlockResult(
        blocked=blocked,
        atr_relative_volatility_pct=atr_relative_volatility_pct,
        threshold_pct=threshold_pct,
        reasons=reasons,
    )


def compute_hard_block(
    metric_name: str,
    value: Decimal,
    threshold_pct: Decimal,
) -> HardBlockResult:
    """Check a single hard-block metric against its threshold.

    Returns HardBlockResult with breached=True when value > threshold.
    """
    breached = value > threshold_pct
    reasons: list[str] = []
    if breached:
        reasons.append(f"{metric_name} {value} exceeds threshold {threshold_pct}")
    return HardBlockResult(
        blocked=breached,
        breached=breached,
        breached_metrics=[metric_name] if breached else [],
        reasons=reasons,
    )
