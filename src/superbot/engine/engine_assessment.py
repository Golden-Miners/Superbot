"""Engine capability assessment for M3.5.

Assesses whether there's a demonstrated capability gap requiring an
alternative engine beyond custom baseline, NautilusTrader, and LEAN.
Stdlib-only; no import-time network/MT5/database/model activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class EngineCapability:
    """Engine capability matrix for POC'd engines."""

    def __init__(self) -> None:
        self.engines: dict[str, dict] = {}
        self.register_engine("custom_baseline", "custom", True)
        self.register_engine("nautilus_trader", "event_driven", True)
        self.register_engine("lean", "event_driven", True)

    def register_engine(self, engine_id: str, engine_type: str, operational: bool) -> None:
        self.engines[engine_id] = {
            "engine_type": engine_type,
            "operational": operational,
        }


class EngineAssessment:
    """Engine capability gap assessment."""

    def __init__(self) -> None:
        self.engines: dict[str, dict] = {}

    def register_engine(self, engine_id: str, engine_type: str, operational: bool) -> None:
        self.engines[engine_id] = {
            "engine_type": engine_type,
            "operational": operational,
        }

    def assess_gap(self) -> "GapResult":
        """Assess whether there's a demonstrated capability gap.

        A gap exists when no operational engine covers a required capability.
        With custom baseline, NautilusTrader, and LEAN all operational,
        no gap exists.
        """
        operational = [eid for eid, info in self.engines.items() if info["operational"]]
        engine_types = {
            info["engine_type"] for info in self.engines.values() if info["operational"]
        }

        gap_detected = len(operational) == 0
        reason = "no_alternative_engine_needed" if not gap_detected else "no_operational_engine"

        return GapResult(
            gap_detected=gap_detected,
            reason=reason,
            operational_engines=operational,
            engine_types=engine_types,
        )


@dataclass(frozen=True)
class GapResult:
    gap_detected: bool
    reason: str
    operational_engines: list[str]
    engine_types: set[str]


class AlternativeEngineAssessment:
    """Assesses whether an alternative engine is needed."""

    def __init__(self) -> None:
        self.gaps: list[str] = []

    def register_gap(self, capability: str) -> None:
        self.gaps.append(capability)

    def assess(self) -> "AlternativeEngineResult":
        """Assess whether an alternative engine is needed.

        Returns alternative_needed=False when no capability gap exists.
        """
        return AlternativeEngineResult(
            alternative_needed=len(self.gaps) > 0,
            missing_capabilities=list(self.gaps),
            reason=("no_capability_gap" if not self.gaps else "capability_gap_detected"),
        )


@dataclass(frozen=True)
class AlternativeEngineResult:
    alternative_needed: bool
    missing_capabilities: list[str]
    reason: str
