"""World grid, tiles, resources, and buildings for AI Agent City."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Terrain(Enum):
    GROUND = "ground"
    WATER = "water"
    ROAD = "road"
    FOREST = "forest"
    MOUNTAIN = "mountain"


@dataclass
class Resource:
    name: str
    quantity: int

    def take(self, amount: int = 1) -> int:
        taken = min(amount, self.quantity)
        self.quantity -= taken
        return taken


@dataclass
class BuildingType:
    name: str
    cost: dict[str, int]
    jobs: int
    produces: Optional[str]


@dataclass
class Building:
    type: BuildingType
    owner_id: Optional[str] = None
    workers: list[str] = field(default_factory=list)
    durability: int = 100

    @property
    def has_vacancy(self) -> bool:
        return len(self.workers) < self.type.jobs


@dataclass
class Tile:
    x: int
    y: int
    terrain: Terrain = Terrain.GROUND
    resources: list[Resource] = field(default_factory=list)
    building: Optional[Building] = None
    agent_ids: list[str] = field(default_factory=list)

    @property
    def is_passable(self) -> bool:
        return self.terrain not in (Terrain.WATER, Terrain.MOUNTAIN)

    def get_resource(self, name: str) -> Optional[Resource]:
        for r in self.resources:
            if r.name == name and r.quantity > 0:
                return r
        return None

    def total_resources(self) -> int:
        return sum(r.quantity for r in self.resources)


class WorldGrid:
    def __init__(self, width: int, height: int, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self.tiles: dict[tuple[int, int], Tile] = {}
        self._rng = random.Random(seed)
        self._generate()

    def _generate(self):
        for x in range(self.width):
            for y in range(self.height):
                terrain = self._random_terrain(x, y)
                tile = Tile(x=x, y=y, terrain=terrain)
                if terrain == Terrain.FOREST:
                    tile.resources.append(Resource("wood", self._rng.randint(1, 2)))
                elif terrain == Terrain.GROUND:
                    if self._rng.random() < 0.15:
                        tile.resources.append(Resource("food", self._rng.randint(1, 3)))
                    if self._rng.random() < 0.05:
                        tile.resources.append(Resource("stone", 1))
                self.tiles[(x, y)] = tile

    def _random_terrain(self, x: int, y: int) -> Terrain:
        r = self._rng.random()
        if r < 0.05:
            return Terrain.WATER
        elif r < 0.15:
            return Terrain.FOREST
        elif r < 0.18:
            return Terrain.MOUNTAIN
        elif r < 0.25:
            return Terrain.ROAD
        return Terrain.GROUND

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        return self.tiles.get((x, y))

    def get_neighbors(self, x: int, y: int, radius: int = 1) -> list[Tile]:
        neighbors = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                tile = self.get_tile(nx, ny)
                if tile is not None:
                    neighbors.append(tile)
        return neighbors

    def get_passable_neighbors(self, x: int, y: int) -> list[Tile]:
        return [t for t in self.get_neighbors(x, y) if t.is_passable]

    def get_tiles_in_radius(self, x: int, y: int, radius: int) -> list[Tile]:
        tiles = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                tile = self.get_tile(x + dx, y + dy)
                if tile is not None:
                    tiles.append(tile)
        return tiles

    def find_random_passable_tile(self) -> Tile:
        while True:
            x = self._rng.randint(0, self.width - 1)
            y = self._rng.randint(0, self.height - 1)
            tile = self.tiles[(x, y)]
            if tile.is_passable:
                return tile

    def place_building(self, x: int, y: int, building: Building) -> bool:
        tile = self.get_tile(x, y)
        if tile is None or not tile.is_passable or tile.building is not None:
            return False
        tile.building = building
        return True

    def regenerate_resources(self, resource_config: list[dict]):
        for pos, tile in self.tiles.items():
            if tile.terrain == Terrain.WATER or tile.terrain == Terrain.MOUNTAIN:
                continue
            for rc in resource_config:
                name = rc["name"]
                regen_rate = rc["regen_rate"]
                max_per_tile = rc["max_per_tile"]
                if regen_rate <= 0 or max_per_tile <= 0:
                    continue
                existing = tile.get_resource(name)
                if existing is not None:
                    if existing.quantity < max_per_tile and self._rng.random() < regen_rate:
                        existing.quantity += 1
                else:
                    if self._rng.random() < regen_rate * 0.5:
                        tile.resources.append(Resource(name, 1))

    def stats(self) -> dict:
        total_resources = 0
        buildings = 0
        agents_on_map = 0
        terrain_counts: dict[str, int] = {}
        for tile in self.tiles.values():
            total_resources += tile.total_resources()
            if tile.building:
                buildings += 1
            agents_on_map += len(tile.agent_ids)
            t = tile.terrain.value
            terrain_counts[t] = terrain_counts.get(t, 0) + 1
        return {
            "total_resources": total_resources,
            "buildings": buildings,
            "agents_on_map": agents_on_map,
            "terrain": terrain_counts,
        }
