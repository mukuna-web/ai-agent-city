"""Reproduction system — agents form partnerships and have children. Every 1000 ticks."""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class ReproductionSystem:
    """
    Handle partnership formation and reproduction.
    Frequency: 1000 (every 1000 ticks — roughly once per "season").
    """

    MIN_PARTNERSHIP_AGE = 5000  # Must be well into adulthood
    MIN_REPRODUCTION_AGE = 5500
    MAX_CHILDREN_PER_HOUSEHOLD = 4

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        from ..engine.event_bus import Event

        alive = world.get_alive_agents()
        adults = [a for a in alive if a.biology.lifecycle_stage in ("adult",)
                  and a.biology.age_ticks >= self.MIN_PARTNERSHIP_AGE]

        # Phase 1: Partnership formation
        singles = [a for a in adults if a.social.partner_id is None]
        random.shuffle(singles)

        for i in range(0, len(singles) - 1, 2):
            a, b = singles[i], singles[i + 1]
            if self._compatible(a, b):
                # Form partnership
                new_a = a.with_social(a.social.set_partner(b.identity.agent_id))
                new_b = b.with_social(b.social.set_partner(a.identity.agent_id))
                world.agents[a.identity.agent_id] = new_a
                world.agents[b.identity.agent_id] = new_b

                event_bus.emit(Event(
                    tick=tick, event_type="agent.partnered",
                    data={"agent_a": a.identity.name, "agent_b": b.identity.name},
                    source_agent_id=a.identity.agent_id,
                ))

        # Phase 2: Reproduction
        partnered = [a for a in world.get_alive_agents()
                     if a.social.partner_id is not None
                     and a.biology.age_ticks >= self.MIN_REPRODUCTION_AGE
                     and a.biology.fertility > 0.3
                     and len(a.social.children_ids) < self.MAX_CHILDREN_PER_HOUSEHOLD]

        for parent_a in partnered:
            partner = world.agents.get(parent_a.social.partner_id)
            if not partner or not partner.biology.is_alive:
                continue

            # Already processed this pair from the other side
            if parent_a.identity.agent_id > partner.identity.agent_id:
                continue

            if self._should_reproduce(parent_a, partner, world):
                child = self._create_child(parent_a, partner, tick)
                world.agents[child.identity.agent_id] = child

                # Update parents
                new_pa = parent_a.with_social(parent_a.social.add_child(child.identity.agent_id))
                new_pb = partner.with_social(partner.social.add_child(child.identity.agent_id))
                world.agents[parent_a.identity.agent_id] = new_pa
                world.agents[partner.identity.agent_id] = new_pb

                event_bus.emit(Event(
                    tick=tick, event_type="agent.born",
                    data={
                        "child_name": child.identity.name,
                        "parent_a": parent_a.identity.name,
                        "parent_b": partner.identity.name,
                        "generation": child.identity.generation,
                    },
                    source_agent_id=child.identity.agent_id,
                ))

    def _compatible(self, a, b) -> bool:
        """Check if two agents would form a partnership."""
        # Personality compatibility
        compat = 1.0 - abs(a.personality.extraversion - b.personality.extraversion) * 0.3
        compat -= abs(a.personality.agreeableness - b.personality.agreeableness) * 0.2

        # Economic compatibility
        income_ratio = min(a.economy.cash, b.economy.cash) / max(a.economy.cash, b.economy.cash, 1)

        return compat > 0.4 and income_ratio > 0.2 and random.random() < 0.3

    def _should_reproduce(self, parent_a, parent_b, world) -> bool:
        """Decide if a couple should have a child."""
        avg_food = (parent_a.needs.food + parent_b.needs.food) / 2
        avg_health = (parent_a.biology.health + parent_b.biology.health) / 2
        combined_cash = parent_a.economy.cash + parent_b.economy.cash
        existing_children = len(parent_a.social.children_ids)

        desire = (
            (1 if avg_food > 0.5 else 0.2) * 0.3 +
            (1 if avg_health > 0.6 else 0.3) * 0.2 +
            (1 if combined_cash > 100 else 0.3) * 0.2 +
            (1 if existing_children < 2 else 0.2) * 0.3
        )

        fertility = min(parent_a.biology.fertility, parent_b.biology.fertility)
        return random.random() < desire * fertility * 0.15

    def _create_child(self, parent_a, parent_b, tick):
        """Create a new child agent inheriting traits from both parents."""
        from ..agents.agent import Agent
        return Agent.create_child(parent_a, parent_b, tick)
