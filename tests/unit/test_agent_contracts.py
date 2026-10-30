"""RED tests for M9.3 — Agent contracts/permissions/proposal store/deterministic orchestration.

Tests define:
- AgentContract: defines what an agent can do (permissions, resources, limits)
- Permission: individual permission entries (read, write, execute, delete on specific resources)
- AgentRegistry: registry of agents and their contracts
- ProposalStore: store of proposals with deterministic evaluation
- Proposal: proposed action with state (pending, approved, rejected, executed)
- Deterministic orchestration: run agents in deterministic order based on priorities
- No AI sets PASS directly: all decisions are deterministic from rules
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from superbot.m9.agent_contracts import (
    AgentContract,
    AgentRegistry,
    PermissionType,
    Proposal,
    ProposalStatus,
    ProposalStore,
    approve_proposal,
    reject_proposal,
)


def test_agent_contract_creates():
    """AgentContract can be created with permissions."""
    contract = AgentContract(
        agent_id="agent_1",
        name="Test Agent",
        permissions=[PermissionType.READ, PermissionType.WRITE],
        max_concurrent_tasks=3,
        max_cost_per_task=Decimal("0.05"),
    )
    assert contract.agent_id == "agent_1"
    assert contract.name == "Test Agent"
    assert PermissionType.READ in contract.permissions
    assert PermissionType.WRITE in contract.permissions
    assert contract.max_concurrent_tasks == 3
    assert contract.max_cost_per_task == Decimal("0.05")


def test_agent_registry_creates():
    """AgentRegistry can be created."""
    registry = AgentRegistry()
    assert registry is not None


def test_register_agent():
    """register_agent adds an agent to the registry."""
    service = AgentRegistry()
    contract = AgentContract(
        agent_id="agent_1",
        name="Test Agent",
        permissions=[PermissionType.READ, PermissionType.WRITE],
        max_concurrent_tasks=3,
        max_cost_per_task=Decimal("0.05"),
    )
    service.register_agent(contract)
    assert service.get_agent("agent_1") is not None


def test_get_unknown_agent():
    """get_agent returns None for unknown agent."""
    registry = AgentRegistry()
    assert registry.get_agent("nonexistent") is None


def test_proposal_creates():
    """Proposal can be created."""
    proposal = Proposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="run_backtest",
        parameters={"strategy": "trend_follow", "symbol": "EURUSD"},
    )
    assert proposal.proposal_id == "prop_1"
    assert proposal.agent_id == "agent_1"
    assert proposal.action == "run_backtest"
    assert proposal.parameters == {"strategy": "trend_follow", "symbol": "EURUSD"}
    assert proposal.status == ProposalStatus.PENDING


def test_proposal_store_creates():
    """ProposalStore can be created."""
    store = ProposalStore()
    assert store is not None


def test_register_proposal():
    """register_proposal adds a proposal to the store."""
    store = ProposalStore()
    proposal = Proposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="run_backtest",
        parameters={"strategy": "trend_follow", "symbol": "EURUSD"},
    )
    store.register_proposal(proposal)
    assert store.get_proposal("prop_1") == proposal


def test_get_unknown_proposal():
    """get_proposal returns None for unknown proposal."""
    store = ProposalStore()
    assert store.get_proposal("nonexistent") is None


def test_approve_proposal():
    """approve_proposal sets proposal status to approved."""
    store = ProposalStore()
    proposal = Proposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="run_backtest",
        parameters={"strategy": "trend_follow", "symbol": "EURUSD"},
    )
    store.register_proposal(proposal)
    result = approve_proposal(store, "prop_1")
    assert result.status == ProposalStatus.APPROVED


def test_reject_proposal():
    """reject_proposal sets proposal status to rejected."""
    store = ProposalStore()
    proposal = Proposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="run_backtest",
        parameters={"strategy": "trend_follow", "symbol": "EURUSD"},
    )
    store.register_proposal(proposal)
    result = reject_proposal(store, "prop_1")
    assert result.status == ProposalStatus.REJECTED


def test_approve_unknown_proposal():
    """approve_proposal raises for unknown proposal."""
    store = ProposalStore()
    with pytest.raises(KeyError):
        approve_proposal(store, "nonexistent")


def test_reject_unknown_proposal():
    """reject_proposal raises for unknown proposal."""
    store = ProposalStore()
    with pytest.raises(KeyError):
        reject_proposal(store, "nonexistent")


def test_deterministic_proposal():
    """Same inputs yield identical proposal results."""
    s1 = ProposalStore()
    s2 = ProposalStore()
    proposal = Proposal(
        proposal_id="prop_1",
        agent_id="agent_1",
        action="run_backtest",
        parameters={"strategy": "trend_follow", "symbol": "EURUSD"},
    )
    s1.register_proposal(proposal)
    s2.register_proposal(proposal)
    r1 = s1.get_proposal("prop_1")
    r2 = s2.get_proposal("prop_1")
    assert r1.proposal_id == r2.proposal_id
    assert r1.agent_id == r2.agent_id


def test_agent_registry_deterministic():
    """Same inputs yield identical agent registry results."""
    s1 = AgentRegistry()
    s2 = AgentRegistry()
    contract = AgentContract(
        agent_id="agent_1",
        name="Test Agent",
        permissions=[PermissionType.READ, PermissionType.WRITE],
        max_concurrent_tasks=3,
        max_cost_per_task=Decimal("0.05"),
    )
    r1 = s1.register_agent(contract)
    r2 = s2.register_agent(contract)
    assert r1.get_agent("agent_1") == r2.get_agent("agent_1")
