"""Tiered cognition engine — 4-level decision system for agent behavior."""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent


@dataclass
class Action:
    """An action an agent intends to perform.

    Attributes:
        action_type: The type of action (e.g. 'find_food', 'go_to_work').
        target: Entity or location ID the action targets.
        params: Additional parameters for the action.
        priority: Priority weight from 0.0 to 1.0.
    """

    action_type: str
    target: str = ""
    params: dict[str, object] = field(default_factory=dict)
    priority: float = 0.5


class AgentCognition:
    """4-tier cognition system. Most decisions are fast symbolic lookups.

    Tier 0 (Reactive): Every tick, <0.01ms. Pure threshold checks.
    Tier 1 (Deliberative): Every 10 ticks. Goal evaluation and plan selection.
    Tier 2 (Strategic): Every 100 ticks. Would use local 1-3B model.
    Tier 3 (Creative): On-demand. Would use full LLM for novel situations.
    """

    def tick(self, agent: Agent, tick: int) -> list[Action]:
        """Main decision loop called every simulation tick.

        Args:
            agent: The agent making decisions.
            tick: Current simulation tick number.

        Returns:
            A list of Actions for the agent to execute this tick.
        """
        # Tier 0: REACTIVE -- every tick, <0.01ms
        urgent = self._reactive(agent)
        if urgent:
            return urgent

        # Tier 1: DELIBERATIVE -- every 10 ticks
        if tick % 10 == 0:
            self._deliberate(agent, tick)

        # Tier 2: STRATEGIC -- every 100 ticks (would use local model)
        if tick % 100 == 0:
            self._strategize(agent, tick)

        # Execute current plan
        return self._execute_plan(agent, tick)

    def _reactive(self, agent: Agent) -> list[Action] | None:
        """Pure symbolic -- thresholds and lookup tables.

        Checks critical needs and returns immediate actions if any
        need falls below its emergency threshold.
        """
        if agent.needs.safety < 0.2:
            return [Action("flee_danger", priority=0.99)]
        if agent.needs.water < 0.1:
            return [Action("find_water", priority=0.98)]
        if agent.needs.health < 0.2:
            return [Action("seek_medical", priority=0.95)]
        if agent.needs.food < 0.1:
            return [Action("find_food", priority=1.0)]
        if agent.needs.rest < 0.1:
            return [Action("go_home_sleep", priority=0.9)]
        return None

    def _deliberate(self, agent: Agent, tick: int) -> None:
        """Evaluate goals and pick plans from known repertoire.

        Finds the most urgent unsatisfied goal and selects a known
        plan template to address it.
        """
        # Placeholder -- will be expanded with plan library
        pass

    def _strategize(self, agent: Agent, tick: int) -> None:
        """Would use local model for medium-term reasoning.

        Placeholder -- in production this calls a local 1-3B parameter model
        for batch inference across agents needing strategic decisions.
        """
        pass

    def _execute_plan(self, agent: Agent, tick: int) -> list[Action]:
        """Execute current step of the active plan.

        If no plan is active, falls back to default behavior:
        go to work if employed, wander if not.
        """
        if agent.goals.active_plan is None:
            if agent.economy.employer_id:
                return [Action("go_to_work", target=agent.economy.employer_id)]
            return [Action("wander")]

        plan = agent.goals.active_plan
        if plan.current_step >= len(plan.steps):
            return [Action("idle")]

        step = plan.steps[plan.current_step]
        return [Action(step.action, target=step.target, params=step.parameters)]
