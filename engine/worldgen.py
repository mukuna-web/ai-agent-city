"""Advanced world generation with biomes, noise-based terrain, rivers, and landmarks."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from engine.world import WorldGrid, Tile, Resource, Building, BuildingType, Terrain


@dataclass
class Biome:
    name: str
    terrain_weights: dict[Terrain, float]
    resources: dict[str, float]  # resource_name -> spawn chance
    color_hint: str  # for visualization


BIOMES = {
    "plains": Biome(
        name="plains",
        terrain_weights={Terrain.GROUND: 0.85, Terrain.ROAD: 0.1, Terrain.WATER: 0.05},
        resources={"food": 0.2, "stone": 0.03},
        color_hint="#5a7a3a",
    ),
    "forest": Biome(
        name="forest",
        terrain_weights={Terrain.FOREST: 0.6, Terrain.GROUND: 0.35, Terrain.WATER: 0.05},
        resources={"wood": 0.3, "food": 0.1},
        color_hint="#2a5a1a",
    ),
    "desert": Biome(
        name="desert",
        terrain_weights={Terrain.GROUND: 0.9, Terrain.MOUNTAIN: 0.08, Terrain.ROAD: 0.02},
        resources={"stone": 0.15},
        color_hint="#a89060",
    ),
    "tundra": Biome(
        name="tundra",
        terrain_weights={Terrain.GROUND: 0.5, Terrain.MOUNTAIN: 0.3, Terrain.WATER: 0.2},
        resources={"stone": 0.1, "wood": 0.05},
        color_hint="#8a9aaa",
    ),
    "coastal": Biome(
        name="coastal",
        terrain_weights={Terrain.GROUND: 0.4, Terrain.WATER: 0.4, Terrain.ROAD: 0.2},
        resources={"food": 0.25},
        color_hint="#4a7a8a",
    ),
}


@dataclass
class Landmark:
    name: str
    x: int
    y: int
    radius: int
    bonus: dict[str, float]  # effect bonuses


class PerlinNoise2D:
    """Simple 2D Perlin-like noise using value noise with interpolation."""

    def __init__(self, seed: int = 42, scale: float = 10.0):
        self._rng = random.Random(seed)
        self.scale = scale
        self._grid: dict[tuple[int, int], float] = {}

    def _gradient(self, ix: int, iy: int) -> float:
        key = (ix, iy)
        if key not in self._grid:
            self._grid[key] = self._rng.uniform(-1, 1)
        return self._grid[key]

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def noise(self, x: float, y: float) -> float:
        sx = x / self.scale
        sy = y / self.scale
        ix = int(math.floor(sx))
        iy = int(math.floor(sy))
        fx = sx - ix
        fy = sy - iy
        u = self._fade(fx)
        v = self._fade(fy)

        n00 = self._gradient(ix, iy)
        n10 = self._gradient(ix + 1, iy)
        n01 = self._gradient(ix, iy + 1)
        n11 = self._gradient(ix + 1, iy + 1)

        x1 = self._lerp(n00, n10, u)
        x2 = self._lerp(n01, n11, u)
        return self._lerp(x1, x2, v)

    def octave_noise(self, x: float, y: float, octaves: int = 3, persistence: float = 0.5) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_val = 0.0
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_val += amplitude
            amplitude *= persistence
            frequency *= 2
        return total / max_val


class WorldGenerator:
    """Enhanced world generator with biomes, rivers, roads, and landmarks."""

    def __init__(self, width: int, height: int, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self._rng = random.Random(seed)
        self.elevation_noise = PerlinNoise2D(seed=seed, scale=12.0)
        self.moisture_noise = PerlinNoise2D(seed=seed + 1, scale=15.0)
        self.biome_map: dict[tuple[int, int], str] = {}
        self.landmarks: list[Landmark] = []

    def generate(self) -> WorldGrid:
        """Generate a complete world with biomes, features, and resources."""
        world = WorldGrid.__new__(WorldGrid)
        world.width = self.width
        world.height = self.height
        world.seed = self.seed
        world.tiles = {}
        world._rng = random.Random(self.seed)

        # Step 1: Generate elevation and moisture maps
        elevation = {}
        moisture = {}
        for x in range(self.width):
            for y in range(self.height):
                elevation[(x, y)] = self.elevation_noise.octave_noise(x, y, octaves=4)
                moisture[(x, y)] = self.moisture_noise.octave_noise(x, y, octaves=3)

        # Step 2: Assign biomes based on elevation + moisture
        for x in range(self.width):
            for y in range(self.height):
                biome = self._classify_biome(elevation[(x, y)], moisture[(x, y)])
                self.biome_map[(x, y)] = biome

        # Step 3: Generate terrain from biomes
        for x in range(self.width):
            for y in range(self.height):
                biome_name = self.biome_map[(x, y)]
                biome = BIOMES[biome_name]
                terrain = self._pick_terrain(biome)
                tile = Tile(x=x, y=y, terrain=terrain)
                world.tiles[(x, y)] = tile

        # Step 4: Generate rivers
        self._generate_rivers(world, elevation)

        # Step 5: Generate road network
        self._generate_roads(world)

        # Step 6: Scatter resources based on biomes
        self._scatter_resources(world)

        # Step 7: Place landmarks
        self._place_landmarks(world)

        # Step 8: Ensure starting zone
        self._ensure_starting_zone(world)

        return world

    def _classify_biome(self, elevation: float, moisture: float) -> str:
        if elevation > 0.4:
            return "tundra"
        if elevation < -0.3:
            return "coastal"
        if moisture > 0.2:
            return "forest"
        if moisture < -0.2:
            return "desert"
        return "plains"

    def _pick_terrain(self, biome: Biome) -> Terrain:
        r = self._rng.random()
        cumulative = 0.0
        for terrain, weight in biome.terrain_weights.items():
            cumulative += weight
            if r <= cumulative:
                return terrain
        return Terrain.GROUND

    def _generate_rivers(self, world: WorldGrid, elevation: dict):
        """Generate 2-3 rivers flowing from high to low elevation."""
        num_rivers = self._rng.randint(2, 3)
        for _ in range(num_rivers):
            # Start from a high point
            high_points = sorted(elevation.items(), key=lambda x: x[1], reverse=True)
            start = high_points[self._rng.randint(0, min(20, len(high_points) - 1))][0]
            x, y = start
            length = 0
            max_length = self.width + self.height

            while 0 <= x < self.width and 0 <= y < self.height and length < max_length:
                tile = world.get_tile(x, y)
                if tile:
                    tile.terrain = Terrain.WATER
                    tile.resources.clear()

                # Flow to lowest neighbor
                neighbors = []
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        neighbors.append(((nx, ny), elevation.get((nx, ny), 0)))

                if not neighbors:
                    break

                # Move toward lowest point with some randomness
                neighbors.sort(key=lambda n: n[1])
                if self._rng.random() < 0.7:
                    next_pos = neighbors[0][0]
                else:
                    next_pos = neighbors[self._rng.randint(0, min(1, len(neighbors) - 1))][0]

                x, y = next_pos
                length += 1

    def _generate_roads(self, world: WorldGrid):
        """Generate roads connecting random points."""
        num_hubs = self._rng.randint(3, 5)
        hubs = []
        for _ in range(num_hubs):
            x = self._rng.randint(5, self.width - 6)
            y = self._rng.randint(5, self.height - 6)
            hubs.append((x, y))

        # Connect hubs with roads
        for i in range(len(hubs) - 1):
            x1, y1 = hubs[i]
            x2, y2 = hubs[i + 1]
            # Simple L-shaped road
            cx, cy = x1, y1
            while cx != x2:
                tile = world.get_tile(cx, cy)
                if tile and tile.terrain not in (Terrain.WATER, Terrain.MOUNTAIN):
                    tile.terrain = Terrain.ROAD
                cx += 1 if x2 > cx else -1
            while cy != y2:
                tile = world.get_tile(cx, cy)
                if tile and tile.terrain not in (Terrain.WATER, Terrain.MOUNTAIN):
                    tile.terrain = Terrain.ROAD
                cy += 1 if y2 > cy else -1

    def _scatter_resources(self, world: WorldGrid):
        """Place resources based on biome distributions."""
        for (x, y), tile in world.tiles.items():
            if tile.terrain in (Terrain.WATER, Terrain.MOUNTAIN):
                continue
            biome_name = self.biome_map.get((x, y), "plains")
            biome = BIOMES[biome_name]
            for resource_name, chance in biome.resources.items():
                if self._rng.random() < chance:
                    qty = self._rng.randint(1, 3)
                    tile.resources.append(Resource(resource_name, qty))

    def _place_landmarks(self, world: WorldGrid):
        """Place special landmarks with bonus effects."""
        landmark_templates = [
            ("Ancient Ruins", {"xp_bonus": 2.0}, 3),
            ("Fertile Valley", {"food_bonus": 1.5, "gather_rate": 1.3}, 4),
            ("Mountain Pass", {"trade_bonus": 0.3}, 2),
            ("Crystal Cave", {"stone_bonus": 3}, 2),
            ("Sacred Grove", {"mood": 0.2, "social_bonus": 0.3}, 3),
        ]
        num_landmarks = self._rng.randint(3, 5)
        placed = []
        for i in range(min(num_landmarks, len(landmark_templates))):
            name, bonus, radius = landmark_templates[i]
            # Find a good spot (not too close to others)
            for _ in range(50):
                x = self._rng.randint(radius, self.width - radius - 1)
                y = self._rng.randint(radius, self.height - radius - 1)
                too_close = any(abs(x - px) < 10 and abs(y - py) < 10 for px, py in placed)
                tile = world.get_tile(x, y)
                if not too_close and tile and tile.is_passable:
                    landmark = Landmark(name=name, x=x, y=y, radius=radius, bonus=bonus)
                    self.landmarks.append(landmark)
                    placed.append((x, y))
                    # Mark area with extra resources
                    for dx in range(-radius, radius + 1):
                        for dy in range(-radius, radius + 1):
                            t = world.get_tile(x + dx, y + dy)
                            if t and t.is_passable:
                                if "food_bonus" in bonus:
                                    t.resources.append(Resource("food", 2))
                                if "stone_bonus" in bonus:
                                    t.resources.append(Resource("stone", int(bonus["stone_bonus"])))
                    break

    def _ensure_starting_zone(self, world: WorldGrid):
        """Make sure center area is hospitable for agent spawning."""
        cx, cy = self.width // 2, self.height // 2
        radius = 5
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                tile = world.get_tile(cx + dx, cy + dy)
                if tile:
                    if tile.terrain in (Terrain.WATER, Terrain.MOUNTAIN):
                        tile.terrain = Terrain.GROUND
                    # Ensure some starting resources
                    if not tile.resources and self._rng.random() < 0.4:
                        tile.resources.append(Resource("food", self._rng.randint(1, 2)))
