"""Agent goals component — goal hierarchy, plans, and plan steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanStep:
    """A single step within a plan.

    Attributes:
        action: Action type — 'move_to', 'work', 'buy', 'sell', 'talk', 'build', 'rest'.
        target: Entity or location ID the action targets.
        parameters: Additional parameters for the action.
        estimated_ticks: Estimated ticks to complete this step.
    """

    action: str
    target: str
    parameters: dict[str, object]
    estimated_ticks: int

    def __post_init__(self) -> None:
        if self.estimated_ticks < 0:
            raise ValueError("estimated_ticks must be non-negative")


@dataclass(frozen=True, slots=True)
class Goal:
    """A single goal with priority and progress tracking.

    Attributes:
        goal_id: Unique identifier for this goal.
        type: Goal category — 'satisfy_need', 'economic', 'social', 'personal'.
        description: Human-readable description of the goal.
        target_condition: Evaluatable condition string for completion.
        priority: Priority weight from 0.0 to 1.0.
        deadline_tick: Tick by which the goal should be met, or None.
        progress: Completion progress from 0.0 to 1.0.
    """

    goal_id: str
    type: str
    description: str
    target_condition: str
    priority: float
    deadline_tick: int | None
    progress: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.priority <= 1.0:
            raise ValueError(f"priority must be between 0.0 and 1.0, got {self.priority}")
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"progress must be between 0.0 and 1.0, got {self.progress}")
        if self.type not in ("satisfy_need", "economic", "social", "personal"):
            raise ValueError(f"Invalid goal type: {self.type!r}")


@dataclass(frozen=True, slots=True)
class Plan:
    """An executable plan composed of ordered steps.

    Attributes:
        plan_id: Unique identifier for this plan.
        goal_id: The goal this plan aims to achieve.
        steps: Ordered tuple of PlanSteps to execute.
        current_step: Index of the step currently being executed.
        status: Plan status — 'executing', 'blocked', 'completed', 'failed'.
    """

    plan_id: str
    goal_id: str
    steps: tuple[PlanStep, ...]
    current_step: int
    status: str

    def __post_init__(self) -> None:
        if self.current_step < 0:
            raise ValueError("current_step must be non-negative")
        if self.status not in ("executing", "blocked", "completed", "failed"):
            raise ValueError(f"Invalid plan status: {self.status!r}")


@dataclass(frozen=True, slots=True)
class AgentGoals:
    """Adaptive goal system with immediate, short-term, and long-term layers.

    Attributes:
        immediate: Goals for this tick (eat, go to work, sleep).
        short_term: Goals for the next ~100 ticks (earn money, fix house).
        long_term: Goals for the next ~10000 ticks (buy house, have child).
        active_plan: Currently executing plan, or None.
    """

    immediate: list[Goal]
    short_term: list[Goal]
    long_term: list[Goal]
    active_plan: Plan | None
