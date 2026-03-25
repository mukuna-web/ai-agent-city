"""Agent social component — relationships, kinship, and reputation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentSocial:
    """Immutable social state for an agent.

    Attributes:
        household_id: ID of the household the agent belongs to, or None.
        partner_id: ID of spouse/partner, or None.
        children_ids: Tuple of child agent IDs.
        parent_ids: Tuple of parent agent IDs (empty for founders).
        friends: Mapping of agent_id to friendship strength (0.0 to 1.0).
        trust: Mapping of agent_id to trust level (0.0 to 1.0).
        reputation: Public reputation score from 0.0 to 1.0.
        social_class: Derived class label — 'lower', 'middle', or 'upper'.
    """

    household_id: str | None
    partner_id: str | None
    children_ids: tuple[str, ...]
    parent_ids: tuple[str, ...]
    friends: dict[str, float]
    trust: dict[str, float]
    reputation: float
    social_class: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.reputation <= 1.0:
            raise ValueError(
                f"reputation must be between 0.0 and 1.0, got {self.reputation}"
            )
        if self.social_class not in ("lower", "middle", "upper"):
            raise ValueError(
                f"Invalid social_class: {self.social_class!r}"
            )
