#!/usr/bin/env python3
"""
Superbot isolated POC control baseline.
Standard-library only. Synthetic fixtures only. No broker connection, no network calls,
no credentials, no production database writes.

This is a correctness/measurement baseline, not a profitable trading strategy or a
production-ready simulator. Run on the target Windows machine to record its actual
resource measurements.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

@dataclass(frozen=True)
class Bar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 1.0

@dataclass(frozen=True)
class Trade:
    side: str
    entry_ts: int
    exit_ts: int
    entry: float
    exit: float
    qty: float
    gross_pnl: float
    costs: float
    net_pnl: float
    reason: str

def fixture() -> list[Bar]:
    # Deliberately tiny deterministic OHLCV fixture. Values are synthetic.
    rows = [
        (1,100,101,99,100),
        (2,100,102,99.5,101),
        (3,101,104,100,103),
        (4,103,105,98,101),  # both TP/SL touch for the active trade: SL must win
        (5,96,99,94,97),     # gap-through stop fixture
        (6,97,100,96,99),
        (7,99,103,98,102),
        (8,102,104,100,101),
        (9,101,102,97,98),
        (10,98,101,96,100),
    ]
    return [Bar(*r) for r in rows]

def bars_hash(bars: Iterable[Bar]) -> str:
    payload = json.dumps([asdict(b) for b in bars], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def assert_ohlcv(bars: list[Bar]) -> None:
    previous = None
    for b in bars:
        assert b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high, f"invalid OHLC at ts={b.ts}"
        assert b.volume >= 0, f"negative volume at ts={b.ts}"
        if previous is not None:
            assert b.ts > previous, "timestamps must be strictly increasing"
        previous = b.ts

def simulate_one(
    bars: list[Bar], entry_index: int, side: str, stop: float, target: float,
    qty: float = 1.0, spread_per_unit: float = 0.0, slippage_per_unit: float = 0.0,
    commission_per_unit: float = 0.0,
) -> Trade:
    """
    Enters at the next bar open. Tests the following bars.
    Conservative rules:
      * If SL and TP both touched in a bar and sequence is unknown, SL first.
      * If a stop is gapped through, fill at the worse opening price.
      * Costs are explicit and deducted from gross P&L.
    """
    if entry_index + 1 >= len(bars):
        raise ValueError("entry signal requires a next bar")
    if side not in ("long", "short"):
        raise ValueError("side must be long or short")
    if qty <= 0:
        raise ValueError("qty must be positive")

    entry_bar = bars[entry_index + 1]
    entry = entry_bar.open + slippage_per_unit if side == "long" else entry_bar.open - slippage_per_unit
    exit_price, exit_ts, reason = None, None, None

    for b in bars[entry_index + 2:]:
        # A stop gap is checked against the bar open first.
        if side == "long" and b.open <= stop:
            exit_price, exit_ts, reason = b.open - slippage_per_unit, b.ts, "stop_gap"
            break
        if side == "short" and b.open >= stop:
            exit_price, exit_ts, reason = b.open + slippage_per_unit, b.ts, "stop_gap"
            break

        if side == "long":
            hit_stop, hit_target = b.low <= stop, b.high >= target
        else:
            hit_stop, hit_target = b.high >= stop, b.low <= target

        if hit_stop:  # conservative stop-first, including both-hit bars
            exit_price, exit_ts, reason = (
                (stop - slippage_per_unit, b.ts, "stop") if side == "long"
                else (stop + slippage_per_unit, b.ts, "stop")
            )
            break
        if hit_target:
            exit_price, exit_ts, reason = (
                (target - slippage_per_unit, b.ts, "target") if side == "long"
                else (target + slippage_per_unit, b.ts, "target")
            )
            break

    if exit_price is None:
        last = bars[-1]
        exit_price, exit_ts, reason = last.close, last.ts, "end_of_data"

    sign = 1.0 if side == "long" else -1.0
    gross = (exit_price - entry) * qty * sign
    # Simplified transparent cost fixture: spread + entry/exit slippage + commissions.
    costs = (spread_per_unit * qty) + (commission_per_unit * qty * 2.0)
    net = gross - costs
    return Trade(side, entry_bar.ts, int(exit_ts), float(entry), float(exit_price),
                 float(qty), float(gross), float(costs), float(net), str(reason))

def risk_gate(equity: float, risk_pct: float, stop_distance: float,
              portfolio_open_risk_pct: float, daily_loss_pct: float,
              drawdown_pct: float) -> tuple[bool, str, float]:
    """Minimal deterministic guard test; real MT5 contract/tick sizing is out of scope."""
    if equity <= 0 or stop_distance <= 0:
        return False, "invalid_equity_or_stop", 0.0
    if risk_pct <= 0 or risk_pct > 5:
        return False, "per_trade_risk_outside_poc_cap", 0.0
    if portfolio_open_risk_pct + risk_pct > 5:
        return False, "portfolio_open_risk_cap", 0.0
    if daily_loss_pct >= 3:
        return False, "daily_loss_limit", 0.0
    if drawdown_pct >= 10:
        return False, "portfolio_drawdown_halt", 0.0
    cash_risk = equity * risk_pct / 100.0
    return True, "accepted", cash_risk / stop_distance

def run_tests() -> dict:
    bars = fixture()
    assert_ohlcv(bars)
    assert len(bars) == 10
    # Long entered at bar index 1 -> next bar open; following bar touches stop and target.
    t = simulate_one(bars, entry_index=1, side="long", stop=99.0, target=104.0)
    assert t.entry_ts == bars[2].ts
    assert t.reason == "stop", f"expected conservative stop-first, got {t.reason}"
    # Explicit cost accounting.
    tc = simulate_one(bars, entry_index=0, side="long", stop=90, target=200,
                      spread_per_unit=0.2, commission_per_unit=0.1)
    assert abs(tc.costs - 0.4) < 1e-9
    assert abs(tc.net_pnl - (tc.gross_pnl - tc.costs)) < 1e-9
    # Stop-gap behavior: entry next open on bar 2, stop below entry; subsequent bar opens below stop.
    gap_bars = [Bar(1,100,101,99,100), Bar(2,100,101,99,100),
                Bar(3,100,102,99,101), Bar(4,94,96,92,95)]
    gap = simulate_one(gap_bars, 1, "long", stop=97, target=120)
    assert gap.reason == "stop_gap", f"expected stop_gap, got {gap.reason}"
    assert gap.exit == 94
    # Risk gates.
    assert risk_gate(10000, 0.5, 2, 1.0, 0.0, 0.0)[0]
    assert not risk_gate(10000, 0.5, 2, 4.8, 0.0, 0.0)[0]
    assert not risk_gate(10000, 0.5, 2, 0.0, 3.0, 0.0)[0]
    assert not risk_gate(10000, 0.5, 2, 0.0, 0.0, 10.0)[0]
    # Chronology/lookahead contract: entry must be on a later bar than the signal.
    assert bars[1].ts < bars[2].ts
    return {
        "status": "PASS",
        "tests": [
            "OHLCV validity and chronological timestamps",
            "next-bar-open entry",
            "ambiguous same-bar SL/TP uses stop-first",
            "explicit spread/commission cost accounting",
            "stop-gap fills at worse opening price",
            "deterministic portfolio/daily-loss/drawdown risk gates",
            "signal timestamp precedes entry timestamp",
        ],
        "fixture_bars": len(bars),
        "fixture_sha256": bars_hash(bars),
        "trade_example": asdict(t),
        "risk_gate_examples": {
            "normal": risk_gate(10000, 0.5, 2, 1.0, 0.0, 0.0),
            "portfolio_cap_breach": risk_gate(10000, 0.5, 2, 4.8, 0.0, 0.0),
        },
    }

def benchmark(repetitions: int = 5, warmups: int = 1) -> dict:
    bars = fixture()
    assert_ohlcv(bars)
    for _ in range(warmups):
        simulate_one(bars, 1, "long", 99.0, 104.0)
    times_ms = []
    peaks = []
    for _ in range(repetitions):
        tracemalloc.start()
        start = time.perf_counter()
        for i in range(2000):
            simulate_one(bars, 1, "long", 99.0, 104.0,
                         spread_per_unit=0.01, commission_per_unit=0.005)
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times_ms.append(elapsed * 1000)
        peaks.append(peak)
    med = statistics.median(times_ms)
    return {
        "warmups": warmups, "repetitions": repetitions, "iterations_per_run": 2000,
        "runtime_ms": times_ms, "median_runtime_ms": med,
        "runtime_range_ms": max(times_ms) - min(times_ms),
        "peak_tracemalloc_bytes": peaks,
        "median_peak_tracemalloc_bytes": statistics.median(peaks),
        "note": "tracemalloc measures Python allocations, not total process RSS; collect process RAM/CPU/disk externally on Windows."
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repetitions", type=int, default=5)
    p.add_argument("--warmups", type=int, default=1)
    args = p.parse_args()
    if args.repetitions < 5:
        p.error("At least five measured repetitions are required by the Superbot benchmark policy.")
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "python": sys.version,
            "processor": platform.processor(),
            "cpu_count_logical": os.cpu_count(),
        },
        "correctness": run_tests(),
        "benchmark": benchmark(args.repetitions, args.warmups),
        "scope_limitations": [
            "Synthetic fixture only; not a market-performance result.",
            "No MT5 connection, broker metadata, or real credentials.",
            "Not a full portfolio simulator; no partial fills, multi-position accounting, swaps, or realistic spread dynamics.",
            "No candidate-engine comparison has been run by this script.",
            "Do not use for live or demo trading.",
        ],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"baseline_{stamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved report: {path}")

if __name__ == "__main__":
    main()
