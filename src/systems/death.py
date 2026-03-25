"""Death system — checks for agent deaths and handles inheritance. Every 100 ticks."""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class DeathSystem:
    """
    Check for deaths, process inheritance, and handle population events.
    Frequency: 100 (every 100 ticks).
    """

    BASE_DEATH_RATE = 0.00001
    ELDER_MULTIPLIER = 5.0
    STARVATION_THRESHOLD = 0.05

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        from ..engine.event_bus import Event

        for agent_id, agent in list(world.agents.items()):
            if not agent.biology.is_alive:
                continue

            if self._should_die(agent):
                cause = self._determine_cause(agent)
                new_bio = agent.biology.die(cause)
                new_agent = agent.with_biology(new_bio)
                world.agents[agent_id] = new_agent

                # Process inheritance
                self._handle_inheritance(agent, world, tick, event_bus)

                event_bus.emit(Event(
                    tick=tick,
                    event_type="agent.died",
                    data={
                        "name": agent.identity.name,
                        "age": agent.biology.age_ticks,
                        "cause": cause,
                        "generation": agent.identity.generation,
                    },
                    source_agent_id=agent_id,
                ))

    def _should_die(self, agent) -> bool:
        death_prob = self.BASE_DEATH_RATE

        if agent.biology.lifecycle_stage == "elder":
            age_beyond = agent.biology.age_ticks - 16000
            death_prob *= self.ELDER_MULTIPLIER * (1 + age_beyond / 5000)

        if agent.biology.health < 0.2:
            death_prob *= 10

        if agent.needs.food < self.STARVATION_THRESHOLD:
            death_prob *= 20

        return random.random() < death_prob

    def _determine_cause(self, agent) -> str:
        if agent.needs.food < self.STARVATION_THRESHOLD:
            return "starvation"
        if agent.biology.health < 0.1:
            return "illness"
        if agent.biology.lifecycle_stage == "elder":
            return "old_age"
        return "unknown"

    def _handle_inheritance(self, deceased, world, tick, event_bus) -> None:
        from ..engine.event_bus import Event

        heirs = []
        if deceased.social.partner_id and deceased.social.partner_id in world.agents:
            heirs.append(deceased.social.partner_id)
        for child_id in deceased.social.children_ids:
            if child_id in world.agents and world.agents[child_id].biology.is_alive:
                heirs.append(child_id)

        if heirs and deceased.economy.cash > 0:
            share = deceased.economy.cash / len(heirs)
            for heir_id in heirs:
                heir = world.agents[heir_id]
                new_econ = heir.economy.add_cash(share)
                world.agents[heir_id] = heir.with_economy(new_econ)

                event_bus.emit(Event(
                    tick=tick,
                    event_type="agent.inherited",
                    data={"heir": heir.identity.name, "amount": share},
                    source_agent_id=heir_id,
                ))
