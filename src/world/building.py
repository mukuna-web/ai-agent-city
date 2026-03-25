"""Building data structure and canonical building-type registry."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


# ---------------------------------------------------------------------------
# Building type registry
# ---------------------------------------------------------------------------

BUILDING_TYPES: dict[str, dict[str, Any]] = {
    "house": {
        "size": 1,
        "capacity": 4,
        "build_cost": {"lumber": 20, "bricks": 30, "tools": 5},
        "build_ticks": 500,
        "maintenance_per_tick": 0.01,
        "requires_power": False,
        "requires_water": True,
    },
    "farm": {
        "size": 4,
        "capacity": 2,
        "build_cost": {"lumber": 10, "tools": 3},
        "build_ticks": 200,
        "output": {"wheat": 0.5, "vegetables": 0.3},
        "requires_power": False,
        "requires_water": True,
    },
    "workshop": {
        "size": 1,
        "capacity": 4,
        "build_cost": {"lumber": 15, "bricks": 20, "iron": 5, "tools": 8},
        "build_ticks": 400,
        "recipes": ["tools", "clothing", "bread"],
        "requires_power": True,
        "requires_water": True,
    },
    "market": {
        "size": 2,
        "capacity": 6,
        "build_cost": {"lumber": 25, "bricks": 40},
        "build_ticks": 600,
        "trade_radius": 20,
        "requires_power": False,
        "requires_water": False,
    },
    "school": {
        "size": 2,
        "capacity": 20,
        "build_cost": {"lumber": 30, "bricks": 50, "tools": 10},
        "build_ticks": 800,
        "skill_boost": 0.002,
        "requires_power": True,
        "requires_water": True,
    },
    "hospital": {
        "size": 2,
        "capacity": 10,
        "build_cost": {"lumber": 20, "bricks": 40, "iron": 10, "tools": 15},
        "build_ticks": 1000,
        "heal_rate": 0.01,
        "requires_power": True,
        "requires_water": True,
    },
    "factory": {
        "size": 4,
        "capacity": 20,
        "build_cost": {"bricks": 100, "iron": 50, "tools": 30},
        "build_ticks": 1500,
        "production_multiplier": 3.0,
        "requires_power": True,
        "requires_water": True,
    },
    "power_plant": {
        "size": 4,
        "capacity": 5,
        "build_cost": {"bricks": 80, "iron": 40, "tools": 20},
        "build_ticks": 2000,
        "output": {"electricity": 50},
        "fuel_consumption": {"coal": 0.5},
        "requires_power": False,
        "requires_water": True,
    },
    "warehouse": {
        "size": 2,
        "build_cost": {"lumber": 30, "bricks": 20},
        "build_ticks": 400,
        "storage_capacity": 1000,
        "requires_power": False,
        "requires_water": False,
    },
    "road_segment": {
        "size": 1,
        "build_cost": {"stone": 5},
        "build_ticks": 50,
        "speed_bonus": 2.0,
    },
    "town_hall": {
        "size": 2,
        "capacity": 10,
        "build_cost": {"lumber": 40, "bricks": 80, "iron": 20},
        "build_ticks": 2000,
        "governance_radius": 50,
        "requires_power": True,
        "requires_water": True,
    },
}


# ---------------------------------------------------------------------------
# Building frozen dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Building:
    """An immutable snapshot of a building placed on the world map."""

    building_id: str
    type: str
    tile_x: int
    tile_y: int
    owner_id: str
    condition: float = 1.0
    construction_progress: float = 0.0
    workers: tuple[str, ...] = ()
    residents: tuple[str, ...] = ()
    inventory: dict[str, float] = None  # type: ignore[assignment]
    is_operational: bool = False
    built_at_tick: int = 0

    def __post_init__(self) -> None:
        if self.inventory is None:
            object.__setattr__(self, "inventory", {})
        if self.type not in BUILDING_TYPES:
            raise ValueError(f"Unknown building type: {self.type!r}")

    # Convenience -----------------------------------------------------------

    @property
    def spec(self) -> dict[str, Any]:
        """Return the canonical spec for this building type."""
        return BUILDING_TYPES[self.type]

    @property
    def is_complete(self) -> bool:
        return self.construction_progress >= 1.0

    def with_progress(self, progress: float, *, operational: bool | None = None) -> Building:
        clamped = max(0.0, min(1.0, progress))
        ops = operational if operational is not None else (clamped >= 1.0)
        return replace(self, construction_progress=clamped, is_operational=ops)

    def with_condition(self, condition: float) -> Building:
        clamped = max(0.0, min(1.0, condition))
        return replace(self, condition=clamped, is_operational=clamped > 0.2 and self.is_complete)

    def with_workers(self, workers: tuple[str, ...]) -> Building:
        return replace(self, workers=workers)

    def with_residents(self, residents: tuple[str, ...]) -> Building:
        return replace(self, residents=residents)

    def with_inventory(self, inventory: dict[str, float]) -> Building:
        return replace(self, inventory=inventory)
