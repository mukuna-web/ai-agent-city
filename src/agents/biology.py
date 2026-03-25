"""Agent biology component — lifecycle stages, health, and aging."""

from __future__ import annotations

from dataclasses import dataclass, replace


# Lifecycle stage thresholds (in ticks)
CHILD_MAX_TICKS: int = 2000
ADOLESCENT_MAX_TICKS: int = 4000
ADULT_MAX_TICKS: int = 16000

# Elder health decay rate per tick
ELDER_HEALTH_DECAY: float = 0.00005
ELDER_MAX_HEALTH_DECAY: float = 0.00003

# Fertility curve parameters
FERTILITY_PEAK_START: int = 6000
FERTILITY_PEAK_END: int = 8000
FERTILITY_DECLINE_RATE: float = 0.00005


def get_lifecycle_stage(age_ticks: int) -> str:
    """Determine lifecycle stage from age in ticks.

    Args:
        age_ticks: Current age in simulation ticks.

    Returns:
        One of 'child', 'adolescent', 'adult', or 'elder'.
    """
    if age_ticks < CHILD_MAX_TICKS:
        return "child"
    if age_ticks < ADOLESCENT_MAX_TICKS:
        return "adolescent"
    if age_ticks < ADULT_MAX_TICKS:
        return "adult"
    return "elder"


@dataclass(frozen=True, slots=True)
class AgentBiology:
    """Immutable biological state for an agent.

    Attributes:
        age_ticks: Current age in simulation ticks.
        lifecycle_stage: Current stage — child, adolescent, adult, or elder.
        health: Current health from 0.0 (dead) to 1.0 (perfect).
        max_health: Maximum achievable health; degrades with elder age.
        fertility: Reproductive capacity from 0.0 to 1.0.
        is_alive: Whether the agent is alive.
        cause_of_death: Description of death cause, or None if alive.
    """

    age_ticks: int
    lifecycle_stage: str
    health: float
    max_health: float
    fertility: float
    is_alive: bool
    cause_of_death: str | None

    def __post_init__(self) -> None:
        if self.age_ticks < 0:
            raise ValueError("age_ticks must be non-negative")
        if not 0.0 <= self.health <= 1.0:
            raise ValueError("health must be between 0.0 and 1.0")
        if not 0.0 <= self.max_health <= 1.0:
            raise ValueError("max_health must be between 0.0 and 1.0")
        if not 0.0 <= self.fertility <= 1.0:
            raise ValueError("fertility must be between 0.0 and 1.0")
        if self.lifecycle_stage not in ("child", "adolescent", "adult", "elder"):
            raise ValueError(
                f"Invalid lifecycle_stage: {self.lifecycle_stage!r}"
            )

    def age_one_tick(self) -> AgentBiology:
        """Advance the agent by one simulation tick.

        Returns a new AgentBiology with updated age, lifecycle stage,
        and health/fertility adjustments for elders.
        """
        if not self.is_alive:
            return self

        new_age = self.age_ticks + 1
        new_stage = get_lifecycle_stage(new_age)
        new_max_health = self.max_health
        new_health = self.health
        new_fertility = self.fertility

        # Elder decay
        if new_stage == "elder":
            new_max_health = max(0.0, self.max_health - ELDER_MAX_HEALTH_DECAY)
            new_health = min(new_health, new_max_health)
            new_health = max(0.0, new_health - ELDER_HEALTH_DECAY)

        # Fertility decline after peak
        if new_age > FERTILITY_PEAK_END:
            new_fertility = max(0.0, self.fertility - FERTILITY_DECLINE_RATE)

        # Check for death
        new_is_alive = new_health > 0.0
        new_cause = None if new_is_alive else "old_age"

        return replace(
            self,
            age_ticks=new_age,
            lifecycle_stage=new_stage,
            health=new_health,
            max_health=new_max_health,
            fertility=new_fertility,
            is_alive=new_is_alive,
            cause_of_death=new_cause if not new_is_alive else self.cause_of_death,
        )
