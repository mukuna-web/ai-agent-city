"""Environment system -- seasons, weather modifiers, and disasters."""

from __future__ import annotations

import random
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEASONS: tuple[str, ...] = ("spring", "summer", "autumn", "winter")
SEASON_LENGTH: int = 2500  # ticks per season
YEAR_LENGTH: int = SEASON_LENGTH * len(SEASONS)


# ---------------------------------------------------------------------------
# World event
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class WorldEvent:
    """An environmental event that affects the simulation."""

    type: str           # "disaster" | "weather" | "event"
    subtype: str        # "flood" | "drought" | "fire" | "epidemic" etc.
    district_id: str
    severity: float     # 0.0 -- 1.0
    tick: int


# ---------------------------------------------------------------------------
# Seasonal modifier tables
# ---------------------------------------------------------------------------

_SEASON_MODIFIERS: dict[str, dict[str, float]] = {
    "spring": {
        "fertility_bonus": 0.3,
        "construction_speed": 1.0,
        "food_decay_mult": 1.0,
    },
    "summer": {
        "fertility_bonus": 0.5,
        "construction_speed": 1.2,
        "food_decay_mult": 1.5,
    },
    "autumn": {
        "fertility_bonus": 0.1,
        "construction_speed": 1.0,
        "food_decay_mult": 1.2,
    },
    "winter": {
        "fertility_bonus": -0.2,
        "construction_speed": 0.6,
        "food_decay_mult": 0.7,
        "heating_cost": 0.5,
        "health_penalty": 0.001,
    },
}

_DISASTER_TYPES: tuple[str, ...] = ("flood", "drought", "fire", "epidemic")
_DISASTER_PROBABILITY: float = 0.0001  # ~1 per 10 000 ticks


# ---------------------------------------------------------------------------
# EnvironmentSystem
# ---------------------------------------------------------------------------

class EnvironmentSystem:
    """Stateless helper that computes seasonal effects and random disasters."""

    # -- Season helpers -----------------------------------------------------

    @staticmethod
    def get_season(tick: int) -> str:
        """Return the current season name for *tick*."""
        cycle = tick % YEAR_LENGTH
        index = cycle // SEASON_LENGTH
        return SEASONS[index]

    @staticmethod
    def get_season_day(tick: int) -> int:
        """Return the day-of-season (0 .. SEASON_LENGTH-1)."""
        return tick % SEASON_LENGTH

    @staticmethod
    def get_year(tick: int) -> int:
        """Return the 0-based year number."""
        return tick // YEAR_LENGTH

    # -- Modifier lookup ----------------------------------------------------

    @classmethod
    def get_modifiers(cls, tick: int) -> dict[str, float]:
        """Return a dict of gameplay modifiers for the current season."""
        season = cls.get_season(tick)
        return dict(_SEASON_MODIFIERS[season])

    # -- Disaster generation ------------------------------------------------

    @classmethod
    def trigger_disaster(
        cls,
        tick: int,
        district_ids: list[str],
        *,
        rng: random.Random | None = None,
    ) -> WorldEvent | None:
        """Possibly generate a random disaster.

        Parameters
        ----------
        tick:
            Current simulation tick.
        district_ids:
            List of district IDs that could be affected.
        rng:
            Optional seeded RNG for reproducibility.

        Returns
        -------
        WorldEvent | None:
            A disaster event, or ``None`` if nothing happened this tick.
        """
        if not district_ids:
            return None

        rand = rng or random
        if rand.random() >= _DISASTER_PROBABILITY:
            return None

        return WorldEvent(
            type="disaster",
            subtype=rand.choice(_DISASTER_TYPES),
            district_id=rand.choice(district_ids),
            severity=rand.uniform(0.3, 1.0),
            tick=tick,
        )
