"""Tests for Superbot configuration profiles (M1.1 / M1.3).

These tests must run without network, MT5, database, or model access.
"""

from __future__ import annotations

import pytest

from superbot.config import InvalidConfigError, Profile, SuperbotConfig


def test_profile_enum_has_research_and_internal_simulation():
    assert Profile.RESEARCH == "research"
    assert Profile.INTERNAL_SIMULATION == "internal-simulation"


def test_valid_profiles_are_accepted():
    for profile in (Profile.RESEARCH, Profile.INTERNAL_SIMULATION):
        cfg = SuperbotConfig(profile=profile)
        assert cfg.profile == profile


def test_invalid_profile_is_rejected():
    with pytest.raises(InvalidConfigError):
        SuperbotConfig(profile="not-a-real-profile")  # type: ignore[arg-type]


def test_demo_readiness_profile_not_available_v1():
    # demo-readiness is a future human-approved gate; not a valid V1 profile.
    with pytest.raises(InvalidConfigError):
        SuperbotConfig(profile="demo-readiness")  # type: ignore[arg-type]
