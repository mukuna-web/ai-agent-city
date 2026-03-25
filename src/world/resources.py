"""Resource type registry for the world economy.

Every resource has a category, weight, base market value, and optional
recipe / spoilage information.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Canonical resource registry
# ---------------------------------------------------------------------------

RESOURCES: dict[str, dict[str, Any]] = {
    # --- RAW MATERIALS (extracted from tiles) ---
    "timber": {
        "category": "raw",
        "weight": 5,
        "base_value": 2,
    },
    "stone": {
        "category": "raw",
        "weight": 10,
        "base_value": 3,
    },
    "iron_ore": {
        "category": "raw",
        "weight": 8,
        "base_value": 5,
    },
    "clay": {
        "category": "raw",
        "weight": 6,
        "base_value": 1,
    },
    "coal": {
        "category": "raw",
        "weight": 7,
        "base_value": 4,
    },

    # --- AGRICULTURAL (grown on fertile tiles) ---
    "wheat": {
        "category": "agricultural",
        "weight": 1,
        "base_value": 1,
        "spoil_ticks": 2000,
    },
    "vegetables": {
        "category": "agricultural",
        "weight": 1,
        "base_value": 2,
        "spoil_ticks": 1000,
    },
    "cotton": {
        "category": "agricultural",
        "weight": 0.5,
        "base_value": 3,
    },
    "livestock": {
        "category": "agricultural",
        "weight": 20,
        "base_value": 15,
    },

    # --- PROCESSED (crafted from raw materials) ---
    "lumber": {
        "category": "processed",
        "weight": 4,
        "base_value": 5,
        "recipe": {"timber": 2},
    },
    "bricks": {
        "category": "processed",
        "weight": 8,
        "base_value": 4,
        "recipe": {"clay": 3, "coal": 1},
    },
    "iron": {
        "category": "processed",
        "weight": 6,
        "base_value": 10,
        "recipe": {"iron_ore": 2, "coal": 1},
    },
    "tools": {
        "category": "processed",
        "weight": 2,
        "base_value": 15,
        "recipe": {"iron": 1, "timber": 1},
    },
    "bread": {
        "category": "processed",
        "weight": 0.5,
        "base_value": 3,
        "recipe": {"wheat": 2},
        "spoil_ticks": 500,
    },
    "cloth": {
        "category": "processed",
        "weight": 0.3,
        "base_value": 8,
        "recipe": {"cotton": 3},
    },
    "meat": {
        "category": "processed",
        "weight": 2,
        "base_value": 8,
        "recipe": {"livestock": 1},
        "spoil_ticks": 800,
    },

    # --- CONSUMABLES ---
    "food": {
        "category": "consumable",
        "weight": 1,
        "base_value": 4,
    },
    "medicine": {
        "category": "consumable",
        "weight": 0.1,
        "base_value": 20,
    },
    "clothing": {
        "category": "consumable",
        "weight": 0.5,
        "base_value": 10,
        "recipe": {"cloth": 2},
    },

    # --- ENERGY ---
    "electricity": {
        "category": "energy",
        "weight": 0,
        "base_value": 1,
    },
    "water_supply": {
        "category": "energy",
        "weight": 0,
        "base_value": 0.5,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_resource(name: str) -> dict[str, Any]:
    """Return a resource definition or raise ``KeyError``."""
    return RESOURCES[name]


def resources_by_category(category: str) -> dict[str, dict[str, Any]]:
    """Return all resources that belong to *category*."""
    return {k: v for k, v in RESOURCES.items() if v["category"] == category}


def get_recipe(resource_name: str) -> dict[str, float]:
    """Return the crafting recipe for *resource_name*, or empty dict."""
    return dict(RESOURCES.get(resource_name, {}).get("recipe", {}))


def get_spoil_ticks(resource_name: str) -> int | None:
    """Return spoilage duration in ticks, or ``None`` if the resource doesn't spoil."""
    return RESOURCES.get(resource_name, {}).get("spoil_ticks")
