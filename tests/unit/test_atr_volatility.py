"""RED tests for M7.5 — ATR-relative volatility and hard blocks; thresholds OPEN, never guessed.

Tests define:
- ATRVolatilityService: computes ATR-relative volatility from price data
- ATRReading: ATR value, current price, ATR-relative volatility percentage
- HardBlockService: hard blocks that pause trading when volatility or loss thresholds breached
- Thresholds are OPEN: never hardcoded; must be provided as explicit configuration inputs
- Volatility block: pause trading when ATR-relative volatility exceeds configured threshold
- Hard block: pause trading when any configured hard-limit metric is breached
- Deterministic: same inputs yield identical results
- Stdlib-only, no import-time network/MT5/database/model activity
"""

from __future__ import annotations

from decimal import Decimal

from superbot.risk.atr_volatility import (
    ATRReading,
    ATRVolatilityService,
    HardBlock,
    HardBlockResult,
    HardBlockService,
    VolatilityBlockResult,
    compute_atr,
    compute_atr_relative_volatility,
    compute_hard_block,
    compute_volatility_block,
)


def test_atr_reading_creates():
    """ATRReading can be created."""
    reading = ATRReading(
        atr=Decimal("1.50"),
        current_price=Decimal("100.00"),
        atr_relative_volatility_pct=Decimal("1.5"),
    )
    assert reading.atr == Decimal("1.50")
    assert reading.current_price == Decimal("100.00")
    assert reading.atr_relative_volatility_pct == Decimal("1.5")


def test_compute_atr():
    """compute_atr computes Average True Range from high/low/close data."""
    # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    candles = [
        {
            "high": Decimal(105),
            "low": Decimal(100),
            "close": Decimal(104),
            "prev_close": Decimal(102),
        },
        {
            "high": Decimal(108),
            "low": Decimal(103),
            "close": Decimal(106),
            "prev_close": Decimal(104),
        },
    ]
    atr = compute_atr(candles)
    assert atr is not None
    assert atr > Decimal(0)


def test_compute_atr_relative_volatility():
    """compute_atr_relative_volatility computes ATR / current_price * 100."""
    result = compute_atr_relative_volatility(Decimal("1.50"), Decimal("100.00"))
    assert result == Decimal("1.5")  # 1.50 / 100.00 * 100 = 1.5


def test_atr_volatility_service_creates():
    """ATRVolatilityService can be created with configurable threshold."""
    service = ATRVolatilityService(volatility_threshold_pct=Decimal("2.0"))
    assert service.volatility_threshold_pct == Decimal("2.0")


def test_compute_volatility_block_not_blocked():
    """compute_volatility_block returns not blocked when ATR-rel vol below threshold."""
    result = compute_volatility_block(Decimal("1.5"), Decimal("2.0"))
    assert result.blocked is False
    assert result.reasons == []


def test_compute_volatility_block_blocked():
    """compute_volatility_block returns blocked when ATR-rel vol exceeds threshold."""
    result = compute_volatility_block(Decimal("2.5"), Decimal("2.0"))
    assert result.blocked is True
    assert (
        "volatility" in " ".join(result.reasons).lower()
        or "atr" in " ".join(result.reasons).lower()
    )


def test_volatility_block_at_threshold():
    """compute_volatility_block not blocked when ATR-rel vol equals threshold."""
    result = compute_volatility_block(Decimal("2.0"), Decimal("2.0"))
    assert result.blocked is False


def test_hard_block_creates():
    """HardBlock can be created."""
    hb = HardBlock(metric_name="daily_loss", threshold_pct=Decimal(3), breached=True)
    assert hb.metric_name == "daily_loss"
    assert hb.threshold_pct == Decimal(3)
    assert hb.breached is True


def test_compute_hard_block_not_breached():
    """compute_hard_block returns not breached when metric below threshold."""
    result = compute_hard_block("daily_loss", Decimal(2), Decimal(3))
    assert result.breached is False


def test_compute_hard_block_breached():
    """compute_hard_block returns breached when metric exceeds threshold."""
    result = compute_hard_block("daily_loss", Decimal(4), Decimal(3))
    assert result.breached is True


def test_hard_block_service_creates():
    """HardBlockService can be created with configurable hard blocks."""
    service = HardBlockService()
    assert service is not None


def test_add_hard_block():
    """HardBlockService can add hard blocks."""
    service = HardBlockService()
    service.add_hard_block("max_dd", Decimal(10))
    assert service.get_hard_block("max_dd") is not None


def test_check_hard_blocks_none_breached():
    """check_hard_blocks returns no breaches when all metrics below thresholds."""
    service = HardBlockService()
    service.add_hard_block("daily_loss", Decimal(3))
    service.add_hard_block("max_dd", Decimal(10))
    result = service.check_hard_blocks({"daily_loss": Decimal(2), "max_dd": Decimal(5)})
    assert result.blocked is False
    assert result.reasons == []


def test_check_hard_blocks_breached():
    """check_hard_blocks returns blocked when any metric exceeds threshold."""
    service = HardBlockService()
    service.add_hard_block("daily_loss", Decimal(3))
    service.add_hard_block("max_dd", Decimal(10))
    result = service.check_hard_blocks({"daily_loss": Decimal(4), "max_dd": Decimal(5)})
    assert result.blocked is True
    assert len(result.reasons) == 1


def test_thresholds_never_hardcoded():
    """ATRVolatilityService does not hardcode thresholds; threshold must be passed explicitly."""
    service1 = ATRVolatilityService(volatility_threshold_pct=Decimal("2.0"))
    service2 = ATRVolatilityService(volatility_threshold_pct=Decimal("5.0"))
    assert service1.volatility_threshold_pct != service2.volatility_threshold_pct


def test_atr_volatility_deterministic():
    """Same inputs yield identical ATR-relative volatility results."""
    ATRVolatilityService(volatility_threshold_pct=Decimal("2.0"))
    ATRVolatilityService(volatility_threshold_pct=Decimal("2.0"))
    r1 = compute_atr_relative_volatility(Decimal("1.50"), Decimal("100.00"))
    r2 = compute_atr_relative_volatility(Decimal("1.50"), Decimal("100.00"))
    assert r1 == r2


def test_volatility_block_result_creates():
    """VolatilityBlockResult can be created."""
    result = VolatilityBlockResult(
        blocked=False,
        atr_relative_volatility_pct=Decimal("1.5"),
        threshold_pct=Decimal("2.0"),
        reasons=[],
    )
    assert result.blocked is False


def test_hard_block_result_creates():
    """HardBlockResult can be created."""
    result = HardBlockResult(blocked=False, breached_metrics=[], reasons=[])
    assert result.blocked is False
