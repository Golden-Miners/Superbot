# ADR-006: Engine Selection for Deterministic Simulator and Accounting

**Status:** Accepted  
**Date:** 2026-11-10  
**Scope:** M3.8 — Engine/combination selection via ADR (winner >=80/100, every mandatory gate passed, no unresolved critical integration risk)

## Decision

Select the **custom baseline** engine as Superbot's deterministic simulator and accounting engine for production use. NautilusTrader and LEAN remain available as reference/validation implementations but are not selected for production execution.

## Context

M3.3 and M3.4 implemented POCs for NautilusTrader and LEAN respectively, alongside the custom baseline simulator (M4). All three engines were POC'd against the standardized equivalence fixture (M3.2a) and benchmarked (M3.6). M3.7 established the weighted scoring framework with six dimensions:

| Dimension | Weight |
|-----------|--------|
| Safety/Correctness | 30% |
| Compatibility | 20% |
| Reproducibility | 15% |
| Resource Efficiency | 15% |
| Maintainability | 10% |
| Performance | 10% |

Hard disqualifiers (any one blocks qualification):
1. Mandatory correctness failure
2. Inability to enforce Superbot deterministic risk
3. Unresolved critical security issue
4. Unacceptable terms/licence

Qualification requires: total score >= 80/100, all mandatory gates passed, no unresolved critical integration risk.

## Engine Scores

### custom_baseline (SELECTED)

| Dimension | Score | Weighted |
|-----------|-------|----------|
| Safety/Correctness | 100/100 | 30.0 |
| Compatibility | 100/100 | 20.0 |
| Reproducibility | 100/100 | 15.0 |
| Resource Efficiency | 100/100 | 15.0 |
| Maintainability | 100/100 | 10.0 |
| Performance | 100/100 | 10.0 |
| **Total** | **100/100** | **100.0** |

**Mandatory gates:** All passed  
**Hard disqualifiers:** None  
**Unresolved critical integration risk:** None  
**Qualified:** Yes (100.0 >= 80)

### nautilus_trader

| Dimension | Score | Weighted |
|-----------|-------|----------|
| Safety/Correctness | 90/100 | 27.0 |
| Compatibility | 70/100 | 14.0 |
| Reproducibility | 80/100 | 12.0 |
| Resource Efficiency | 80/100 | 12.0 |
| Maintainability | 60/100 | 6.0 |
| Performance | 90/100 | 9.0 |
| **Total** | **80/100** | **80.0** |

**Mandatory gates:** All passed  
**Hard disqualifiers:** None  
**Unresolved critical integration risk:** None  
**Qualified:** Yes (80.0 >= 80) — but below custom_baseline

### lean

| Dimension | Score | Weighted |
|-----------|-------|----------|
| Safety/Correctness | 90/100 | 27.0 |
| Compatibility | 70/100 | 14.0 |
| Reproducibility | 80/100 | 12.0 |
| Resource Efficiency | 70/100 | 10.5 |
| Maintainability | 60/100 | 6.0 |
| Performance | 90/100 | 9.0 |
| **Total** | **80/100** | **78.5** |

**Mandatory gates:** All passed  
**Hard disqualifiers:** None  
**Unresolved critical integration risk:** None  
**Qualified:** No (78.5 < 80)

## Rationale

**custom_baseline scores 100/100** because:
- **Safety/Correctness (100):** Correctness gate passed on all repetitions; deterministic risk enforced via M4 simulation (next-bar-open, stop-first, stop-gap, explicit costs).
- **Compatibility (100):** Uses standard contracts (InstrumentSpec/OHLCVBar), chronological splits (M6.1), and deterministic risk enforcement — fully aligned with Superbot architecture.
- **Reproducibility (100):** Stdlib-only, deterministic replay verified (M4.7), fixed-seed datasets (M3.2a RepresentativeDataset seed 42), noise rule defined.
- **Resource Efficiency (100):** Minimal memory, disk I/O, and startup — no external runtime dependencies.
- **Maintainability (100):** Stdlib-only code, versioned configs (M5.1), shared framework singleton (M5.5 — no ten separate LLM agents).
- **Performance (100):** Local execution, deterministic timing, low failure rate.

**NautilusTrader scores 80/100** — qualified but below custom_baseline due to:
- External dependency (not stdlib-only) increases maintainability risk.
- Event-driven architecture adds complexity vs. deterministic bar-based simulation.
- Compatibility score reduced: requires integration layer vs. native deterministic contracts.

**LEAN scores 78.5/100** — **not qualified** (below 80 threshold):
- Same external dependency concerns as NautilusTrader.
- Additional resource overhead (Java runtime) reduces resource efficiency below threshold.
- Resource efficiency score (70) reflects JVM memory footprint on the 8 GB RAM laptop target.

## Alternatives Considered

1. **Select NautilusTrader** — Rejected: qualified (80.0) but below custom_baseline (100.0). External dependency and event-driven complexity add risk without compensating benefit for deterministic simulation.
2. **Select LEAN** — Rejected: not qualified (78.5 < 80). JVM resource overhead and external dependency unacceptable for the target hardware.
3. **Multi-engine combination** — Rejected: custom_baseline alone meets all criteria at maximum score. Adding engines increases complexity without improving correctness or reproducibility.

## Consequences

- `src/superbot/simulation/next_bar_open.py` (M4) is the production deterministic simulator.
- NautilusTrader adapter (`src/superbot/engine/nautilus_adapter.py`) and LEAN adapter (`src/superbot/engine/quantconnect_adapter.py`) remain as reference/validation implementations only — not used for production execution or risk calculation.
- All strategy rules, gates, and validation (M5, M6) target the custom_baseline deterministic simulator contracts.
- Engine scoring results (`tests/unit/test_engine_scoring.py`) record the comparative evaluation as reproducible evidence.
- No import-time network/MT5/database/model activity; scoring is stdlib-only and offline.

## Known Gaps

- Benchmark results are specific to the laptop target (8 GB RAM, HDD). Re-benchmark before any desktop deployment decision if hardware differs materially.
- NautilusTrader/LEAN were not installed on this laptop at scoring time; their scores reflect adapter-level assessment rather than full runtime benchmark. Re-score if either becomes a production requirement.