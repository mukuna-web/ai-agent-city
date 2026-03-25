"""World engine -- tile grid, buildings, districts, resources, and environment."""

from src.world.building import BUILDING_TYPES, Building
from src.world.construction import ConstructionSystem
from src.world.district import District
from src.world.environment import (
    SEASON_LENGTH,
    SEASONS,
    YEAR_LENGTH,
    EnvironmentSystem,
    WorldEvent,
)
from src.world.resources import RESOURCES, get_recipe, get_resource, get_spoil_ticks, resources_by_category
from src.world.tile import TERRAIN_TYPES, ZONE_TYPES, Tile
from src.world.world_map import WorldMap

__all__ = [
    # tile
    "Tile",
    "TERRAIN_TYPES",
    "ZONE_TYPES",
    # district
    "District",
    # building
    "Building",
    "BUILDING_TYPES",
    # resources
    "RESOURCES",
    "get_recipe",
    "get_resource",
    "get_spoil_ticks",
    "resources_by_category",
    # world map
    "WorldMap",
    # construction
    "ConstructionSystem",
    # environment
    "EnvironmentSystem",
    "WorldEvent",
    "SEASONS",
    "SEASON_LENGTH",
    "YEAR_LENGTH",
]
