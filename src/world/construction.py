"""Construction system -- building creation and progress tracking."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import replace

from src.world.building import BUILDING_TYPES, Building
from src.world.tile import Tile


class ConstructionSystem:
    """Manages the lifecycle of building construction.

    All methods are pure-functional: they return new immutable objects rather
    than mutating existing state.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_construction(
        self,
        builder_inventory: dict[str, float],
        building_type: str,
        tile: Tile,
        tick: int,
        owner_id: str,
    ) -> tuple[Building | None, dict[str, float]]:
        """Begin constructing a building on *tile*.

        Parameters
        ----------
        builder_inventory:
            The builder's current resource inventory (will **not** be mutated).
        building_type:
            Key into :data:`BUILDING_TYPES`.
        tile:
            Target tile (must be empty).
        tick:
            Current simulation tick.
        owner_id:
            Agent or firm that owns the building.

        Returns
        -------
        tuple:
            ``(building, new_inventory)`` on success, or
            ``(None, original_inventory)`` if the builder cannot afford it.
        """
        if building_type not in BUILDING_TYPES:
            return None, builder_inventory

        spec = BUILDING_TYPES[building_type]
        cost: dict[str, float] = spec.get("build_cost", {})

        # Check affordability
        for resource, amount in cost.items():
            if builder_inventory.get(resource, 0.0) < amount:
                return None, builder_inventory

        # Deduct resources (immutably)
        new_inventory = dict(builder_inventory)
        for resource, amount in cost.items():
            new_inventory[resource] = new_inventory[resource] - amount

        building = Building(
            building_id=str(_uuid.uuid4()),
            type=building_type,
            tile_x=tile.x,
            tile_y=tile.y,
            owner_id=owner_id,
            condition=1.0,
            construction_progress=0.0,
            workers=(),
            residents=(),
            inventory={},
            is_operational=False,
            built_at_tick=tick,
        )

        return building, new_inventory

    def advance_construction(
        self,
        building: Building,
        worker_skills: list[float],
    ) -> Building:
        """Advance construction by one tick.

        Parameters
        ----------
        building:
            The building under construction.
        worker_skills:
            List of construction skill levels (one per worker).

        Returns
        -------
        Building:
            Updated building with incremented progress (and ``is_operational``
            set to *True* when complete).
        """
        if building.construction_progress >= 1.0:
            return building

        spec = BUILDING_TYPES[building.type]
        build_ticks: int = spec.get("build_ticks", 1)

        skill_sum = sum(worker_skills) if worker_skills else 0.1
        progress_per_tick = skill_sum / build_ticks

        new_progress = min(building.construction_progress + progress_per_tick, 1.0)
        is_complete = new_progress >= 1.0

        return replace(
            building,
            construction_progress=new_progress,
            is_operational=is_complete,
        )

    def estimate_ticks_remaining(
        self,
        building: Building,
        worker_skills: list[float],
    ) -> int:
        """Estimate the number of ticks until construction is complete."""
        if building.construction_progress >= 1.0:
            return 0

        spec = BUILDING_TYPES[building.type]
        build_ticks: int = spec.get("build_ticks", 1)
        skill_sum = sum(worker_skills) if worker_skills else 0.1
        progress_per_tick = skill_sum / build_ticks

        if progress_per_tick <= 0:
            return 999_999

        remaining = 1.0 - building.construction_progress
        return max(1, int(remaining / progress_per_tick))
