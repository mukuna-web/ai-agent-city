"""Agent personality component — Big Five traits with inheritance mechanics."""

from __future__ import annotations

import random
from dataclasses import dataclass


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def _inherit_trait(parent_a_val: float, parent_b_val: float) -> float:
    """Midpoint of parents plus gaussian noise, clamped to [0, 1]."""
    midpoint = (parent_a_val + parent_b_val) / 2.0
    noise = random.gauss(0.0, 0.1)
    return _clamp(midpoint + noise)


@dataclass(frozen=True, slots=True)
class AgentPersonality:
    """Big Five personality traits, fixed at birth with slight drift through inheritance.

    All trait values range from 0.0 to 1.0.

    Attributes:
        openness: Curiosity, creativity, willingness to try new things.
        conscientiousness: Discipline, reliability, organization.
        extraversion: Sociability, energy, assertiveness.
        agreeableness: Cooperation, trust, helpfulness.
        neuroticism: Emotional volatility, anxiety, moodiness.
    """

    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float

    def __post_init__(self) -> None:
        for attr in ("openness", "conscientiousness", "extraversion",
                     "agreeableness", "neuroticism"):
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")

    @property
    def risk_tolerance(self) -> float:
        """Derived trait: willingness to take risks.

        Higher openness and lower neuroticism increase risk tolerance.
        """
        return _clamp(self.openness * (1.0 - self.neuroticism))

    @property
    def ambition(self) -> float:
        """Derived trait: drive to achieve and advance.

        Higher conscientiousness increases ambition; high agreeableness
        slightly tempers it (cooperative vs. competitive).
        """
        return _clamp(self.conscientiousness * (1.0 - self.agreeableness * 0.3))

    @classmethod
    def random(cls) -> AgentPersonality:
        """Generate a random personality with gaussian-distributed traits.

        Traits are drawn from a normal distribution centered at 0.5
        with standard deviation 0.15, clamped to [0.05, 0.95].
        """
        def _rand_trait() -> float:
            return _clamp(random.gauss(0.5, 0.15), 0.05, 0.95)

        return cls(
            openness=_rand_trait(),
            conscientiousness=_rand_trait(),
            extraversion=_rand_trait(),
            agreeableness=_rand_trait(),
            neuroticism=_rand_trait(),
        )

    @classmethod
    def inherit(
        cls, parent_a: AgentPersonality, parent_b: AgentPersonality
    ) -> AgentPersonality:
        """Create a child personality by blending two parents with gaussian noise.

        Each trait is the midpoint of the two parents plus N(0, 0.1) noise,
        clamped to [0, 1].
        """
        return cls(
            openness=_inherit_trait(parent_a.openness, parent_b.openness),
            conscientiousness=_inherit_trait(
                parent_a.conscientiousness, parent_b.conscientiousness
            ),
            extraversion=_inherit_trait(
                parent_a.extraversion, parent_b.extraversion
            ),
            agreeableness=_inherit_trait(
                parent_a.agreeableness, parent_b.agreeableness
            ),
            neuroticism=_inherit_trait(
                parent_a.neuroticism, parent_b.neuroticism
            ),
        )
