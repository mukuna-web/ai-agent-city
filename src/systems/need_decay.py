"""Need decay system — runs EVERY TICK. Agents get hungrier, thirstier, more tired."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class NeedDecaySystem:
    """Decay all agent needs each tick. Frequency: 1 (every tick)."""

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        from ..engine.event_bus import Event

        for agent_id, agent in list(world.agents.items()):
            if not agent.biology.is_alive:
                continue

            # Decay needs
            new_needs = agent.needs.decay_one_tick()

            # Age the agent
            new_bio = agent.biology.age_one_tick()

            # Health declines if food or water critically low
            if new_needs.food < 0.05 or new_needs.water < 0.05:
                health_penalty = 0.002
                new_bio = new_bio.with_health(new_bio.health - health_penalty)

            new_agent = agent.with_needs(new_needs).with_biology(new_bio)
            world.agents[agent_id] = new_agent

            # Emit warning events for critical needs
            if new_needs.food < 0.1 and tick % 50 == 0:
                event_bus.emit(Event(
                    tick=tick,
                    event_type="agent.starving",
                    data={"food_level": new_needs.food},
                    source_agent_id=agent_id,
                ))
