"""Agent needs component — Maslow-inspired need hierarchy with decay mechanics."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace


# Decay rates per tick for each need
FOOD_DECAY: float = 0.002
WATER_DECAY: float = 0.003
SHELTER_DECAY: float = 0.0005
REST_DECAY: float = 0.0015
HEALTH_DECAY: float = 0.0001
SAFETY_DECAY: float = 0.0003
BELONGING_DECAY: float = 0.0002
ESTEEM_DECAY: float = 0.0001
SELF_ACTUALIZATION_DECAY: float = 0.00005

_DECAY_RATES: dict[str, float] = {
    "food": FOOD_DECAY,
    "water": WATER_DECAY,
    "shelter": SHELTER_DECAY,
    "rest": REST_DECAY,
    "health": HEALTH_DECAY,
    "safety": SAFETY_DECAY,
    "belonging": BELONGING_DECAY,
    "esteem": ESTEEM_DECAY,
    "self_actualization": SELF_ACTUALIZATION_DECAY,
}

_NEED_NAMES: tuple[str, ...] = tuple(_DECAY_RATES.keys())


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


@dataclass(frozen=True, slots=True)
class AgentNeeds:
    """Maslow-inspired needs hierarchy. Each value ranges from 0.0 (desperate) to 1.0 (satisfied).

    Attributes:
        food: Hunger level.
        water: Thirst level.
        shelter: Housing security.
        rest: Sleep/energy level.
        health: Physical wellbeing.
        safety: Perceived safety from threats.
        belonging: Social connection satisfaction.
        esteem: Status and recognition.
        self_actualization: Personal growth and purpose.
    """

    food: float
    water: float
    shelter: float
    rest: float
    health: float
    safety: float
    belonging: float
    esteem: float
    self_actualization: float

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{f.name} must be between 0.0 and 1.0, got {value}"
                )

    def decay_one_tick(self) -> AgentNeeds:
        """Apply per-tick decay to all needs, returning a new instance.

        Each need decreases by its configured decay rate, clamped to [0, 1].
        """
        updates: dict[str, float] = {}
        for name, rate in _DECAY_RATES.items():
            current = getattr(self, name)
            updates[name] = _clamp(current - rate)
        return replace(self, **updates)

    def min_need(self) -> float:
        """Return the lowest need value across all needs."""
        return min(getattr(self, name) for name in _NEED_NAMES)

    def most_urgent(self) -> str:
        """Return the name of the need with the lowest value."""
        return min(_NEED_NAMES, key=lambda name: getattr(self, name))

    def satisfy(self, need_name: str, amount: float) -> AgentNeeds:
        """Increase a specific need by the given amount, returning a new instance.

        Args:
            need_name: The need to satisfy (e.g. 'food', 'rest').
            amount: The amount to add (can be negative to reduce).

        Returns:
            A new AgentNeeds with the updated value clamped to [0, 1].

        Raises:
            ValueError: If need_name is not a valid need.
        """
        if need_name not in _NEED_NAMES:
            raise ValueError(
                f"Unknown need: {need_name!r}. Valid needs: {_NEED_NAMES}"
            )
        current = getattr(self, need_name)
        new_value = _clamp(current + amount)
        return replace(self, **{need_name: new_value})

    def to_vector(self) -> list[float]:
        """Return all need values as a list in field declaration order."""
        return [getattr(self, name) for name in _NEED_NAMES]
