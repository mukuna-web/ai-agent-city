"""Production system -- firms produce goods using labour and raw materials."""

from __future__ import annotations

from typing import Any

from src.world.building import BUILDING_TYPES, Building
from src.world.resources import RESOURCES


# ---------------------------------------------------------------------------
# Building-type to profession mapping
# ---------------------------------------------------------------------------

BUILDING_PROFESSION_MAP: dict[str, str] = {
    "farm": "farming",
    "workshop": "crafting",
    "factory": "manufacturing",
    "power_plant": "engineering",
    "hospital": "medicine",
    "school": "teaching",
    "market": "trading",
}


# ---------------------------------------------------------------------------
# ProductionSystem
# ---------------------------------------------------------------------------

class ProductionSystem:
    """Calculates per-tick production output for a firm given its building and workers."""

    @staticmethod
    def get_profession_for_building(building_type: str) -> str:
        """Return the profession relevant to *building_type*."""
        return BUILDING_PROFESSION_MAP.get(building_type, "general")

    def produce(
        self,
        building: Building,
        worker_skills: list[dict[str, float]],
        firm_inventory: dict[str, float],
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Run one tick of production.

        Parameters
        ----------
        building:
            The operational building where production happens.
        worker_skills:
            One ``{profession: level}`` dict per worker.
        firm_inventory:
            Current firm inventory (will **not** be mutated).

        Returns
        -------
        tuple:
            ``(produced, new_inventory)`` where *produced* maps resource
            names to quantities produced this tick, and *new_inventory* is
            the firm inventory after consuming ingredients.
        """
        if not building.is_operational:
            return {}, dict(firm_inventory)

        spec: dict[str, Any] = BUILDING_TYPES.get(building.type, {})
        profession = self.get_profession_for_building(building.type)

        produced: dict[str, float] = {}
        new_inventory = dict(firm_inventory)

        # --- Direct output (farms, power plants) ---------------------------
        output_direct: dict[str, float] = spec.get("output", {})
        if output_direct and worker_skills:
            total_skill = sum(
                ws.get(profession, 0.1) for ws in worker_skills
            )
            for resource, rate in output_direct.items():
                amount = rate * total_skill * len(worker_skills)
                produced[resource] = produced.get(resource, 0.0) + amount

        # --- Recipe-based production (workshops, factories) ----------------
        recipes: list[str] = spec.get("recipes", [])
        production_mult: float = spec.get("production_multiplier", 1.0)

        for recipe_name in recipes:
            recipe: dict[str, float] = RESOURCES.get(recipe_name, {}).get("recipe", {})
            if not recipe:
                continue

            # How many batches can the inventory support?
            max_batches = float("inf")
            for ingredient, amount_needed in recipe.items():
                available = new_inventory.get(ingredient, 0.0)
                if amount_needed <= 0:
                    continue
                batches = available / amount_needed
                max_batches = min(max_batches, batches)

            if max_batches <= 0 or max_batches == float("inf"):
                continue

            # Worker capacity limits output
            worker_capacity = sum(
                ws.get(profession, 0.1) for ws in worker_skills
            ) * production_mult if worker_skills else 0.0

            batches = min(max_batches, worker_capacity)
            if batches <= 0:
                continue

            produced[recipe_name] = produced.get(recipe_name, 0.0) + batches

            # Consume ingredients
            for ingredient, amount_needed in recipe.items():
                consumed = amount_needed * batches
                new_inventory[ingredient] = new_inventory.get(ingredient, 0.0) - consumed

        return produced, new_inventory
