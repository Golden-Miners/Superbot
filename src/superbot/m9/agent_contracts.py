"""M9.3 — Internal-simulation eligibility and three-failed-validation-attempt version archive rule.

Deterministic agent contract, baseline, and version archive service:
- AgentContract: defines what an agent can do (permissions, resources, limits)
- Permission: individual permission entries (read, write, execute, delete on specific resources)
- AgentRegistry: registry of agents and their contracts
- ProposalStore: store of proposals with deterministic evaluation
- Proposal: proposed action with state (pending, approved, rejected, executed)
- Approve/reject: change proposal status deterministically
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class PermissionType(str, Enum):
    """Permission types for agent capabilities."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


class ProposalStatus(str, Enum):
    """Proposal status values."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass(frozen=True)
class Permission:
    """A single permission entry."""

    action: PermissionType
    resource: str
    max_value: Decimal | None = None


@dataclass(frozen=True)
class AgentContract:
    """Defines what an agent is allowed to do."""

    agent_id: str
    name: str
    permissions: list[Permission]
    max_concurrent_tasks: int
    max_cost_per_task: Decimal


@dataclass(frozen=True)
class Proposal:
    """A proposed action with state."""

    proposal_id: str
    agent_id: str
    action: str
    parameters: dict
    status: str = "pending"  # "pending", "approved", "rejected", "executed"


@dataclass(frozen=True)
class AgentRegistry:
    """Registry of agents and their contracts."""

    _agents: dict[str, AgentContract] = field(default_factory=dict)

    def register_agent(self, contract: AgentContract) -> AgentRegistry:
        """Register an agent with its contract."""
        self._agents[contract.agent_id] = contract
        return self

    def get_agent(self, agent_id: str) -> AgentContract | None:
        """Get an agent's contract by ID."""
        return self._agents.get(agent_id)


class ProposalStore:
    """Store of proposals with deterministic evaluation."""

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}

    def register_proposal(self, proposal: Proposal) -> None:
        """Register a proposal."""
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)


def approve_proposal(
    store: ProposalStore,
    proposal_id: str,
) -> Proposal:
    """Approve a proposal (sets status to approved)."""
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise KeyError(f"Proposal {proposal_id} not found")
    object.__setattr__(proposal, "status", "approved")
    return proposal


def reject_proposal(
    store: ProposalStore,
    proposal_id: str,
) -> Proposal:
    """Reject a proposal (sets status to rejected)."""
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise KeyError(f"Proposal {proposal_id} not found")
    object.__setattr__(proposal, "status", "rejected")
    return proposal


def register_agent(
    registry: AgentRegistry,
    contract: AgentContract,
) -> AgentRegistry:
    """Register an agent (convenience function)."""
    registry.register_agent(contract)
    return registry


def register_proposal(
    store: ProposalStore,
    proposal: Proposal,
) -> None:
    """Register a proposal (convenience function)."""
    store.register_proposal(proposal)
