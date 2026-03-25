"""Agent cognition system — runs every tick, dispatches tiered thinking."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class AgentCognitionSystem:
    """
    Run agent cognition for all alive agents.
    Frequency: 1 (every tick), but internal tiers run at different rates.
    """

    def __init__(self, learning_system=None):
        self._learning_system = learning_system

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        from ..agents.cognition import AgentCognition, Action
        from ..engine.event_bus import Event

        cognition = AgentCognition(learning_system=self._learning_system)

        # Capture pre-action snapshots for learning
        if self._learning_system is not None:
            self._learning_system.capture_snapshots(world)

        for agent_id, agent in list(world.agents.items()):
            if not agent.biology.is_alive:
                continue
            if agent.biology.lifecycle_stage == "child":
                continue  # Children don't make decisions

            actions = cognition.tick(agent, tick)

            for action in actions:
                self._execute_action(world, agent_id, action, tick, event_bus)

    def _execute_action(
        self,
        world: "WorldState",
        agent_id: str,
        action: "Action",
        tick: int,
        event_bus: "EventBus",
    ) -> None:
        from ..engine.event_bus import Event

        agent = world.agents.get(agent_id)
        if not agent:
            return

        if action.action_type == "find_food":
            # Try to eat from inventory or buy from market
            current_food = agent.needs.food
            new_agent = agent.with_needs(agent.needs.satisfy("food", 0.3))
            world.agents[agent_id] = new_agent
            event_bus.emit(Event(
                tick=tick, event_type="agent.ate",
                data={"food_before": current_food, "food_after": new_agent.needs.food},
                source_agent_id=agent_id,
            ))

        elif action.action_type == "find_water":
            new_agent = agent.with_needs(agent.needs.satisfy("water", 0.4))
            world.agents[agent_id] = new_agent

        elif action.action_type == "go_home_sleep":
            new_agent = agent.with_needs(agent.needs.satisfy("rest", 0.5))
            world.agents[agent_id] = new_agent

        elif action.action_type == "go_to_work":
            # Agent works — improve skills and earn wage
            profession = agent.economy.profession
            if profession:
                from ..agents.skills import SkillSystem
                skill_system = SkillSystem()
                new_skills = skill_system.practice(agent.skills, profession, intensity=1.0)
                new_econ = agent.economy  # Wage paid by production system
                new_agent = agent.with_skills(new_skills)
                world.agents[agent_id] = new_agent

        elif action.action_type == "wander":
            # Slightly satisfy belonging need from social contact
            if tick % 20 == 0:
                new_agent = agent.with_needs(agent.needs.satisfy("belonging", 0.02))
                world.agents[agent_id] = new_agent

        elif action.action_type == "seek_medical":
            # Heal if hospital exists
            new_agent = agent.with_needs(agent.needs.satisfy("health", 0.1))
            new_bio = agent.biology.with_health(min(agent.biology.health + 0.05, agent.biology.max_health))
            new_agent = new_agent.with_biology(new_bio)
            world.agents[agent_id] = new_agent
