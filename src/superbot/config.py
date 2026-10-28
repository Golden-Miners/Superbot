"""Validated Superbot configuration profiles (M1.1 / M1.3).

Profiles:
  research            - data research, signal generation, historical testing
  internal-simulation - deterministic internal simulation only

`demo-readiness` is a future human-approved gate and is NOT a valid V1 profile.
No secrets are stored here; secret references live in protected local storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvalidConfigError(ValueError):
    """Raised when configuration values fail validation."""


class Profile(str, Enum):
    RESEARCH = "research"
    INTERNAL_SIMULATION = "internal-simulation"


# Future guarded profile; intentionally not accepted by SuperbotConfig in V1.
_DEMO_READINESS = "demo-readiness"


@dataclass(frozen=True)
class SuperbotConfig:
    profile: Profile

    def __post_init__(self) -> None:
        if not isinstance(self.profile, Profile):
            raise InvalidConfigError(
                f"invalid profile {self.profile!r}; expected one of {[p.value for p in Profile]}"
            )
        if self.profile.value == _DEMO_READINESS:
            raise InvalidConfigError(
                "demo-readiness is not a valid V1 profile; future human-approved gate only"
            )
