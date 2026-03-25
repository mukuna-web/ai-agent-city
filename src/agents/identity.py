"""Agent identity component — immutable identification and lineage tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """Immutable identity for an agent in the simulation.

    Attributes:
        agent_id: Unique UUID string identifying this agent.
        name: Human-readable display name.
        birth_tick: The simulation tick when the agent was born/created.
        parent_ids: Tuple of two parent agent IDs, or None for founders.
        generation: Generational depth (0 = founding population).
    """

    agent_id: str
    name: str
    birth_tick: int
    parent_ids: tuple[str, str] | None
    generation: int

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if self.generation < 0:
            raise ValueError("generation must be non-negative")
