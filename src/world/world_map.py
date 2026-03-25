"""WorldMap -- 2-D tile grid with district overlay and A* pathfinding."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, replace

from src.world.district import District
from src.world.tile import Tile


# ---------------------------------------------------------------------------
# Movement cost table (terrain -> base cost in ticks)
# ---------------------------------------------------------------------------

_TERRAIN_COST: dict[str, float] = {
    "grass": 1.0,
    "forest": 1.5,
    "sand": 1.2,
    "rock": 2.0,
    "mountain": 3.0,
    "water": 999.0,  # impassable without bridge
}


# ---------------------------------------------------------------------------
# WorldMap
# ---------------------------------------------------------------------------

class WorldMap:
    """A width x height grid of :class:`Tile` objects with district support.

    The map uses row-major storage: ``_tiles[y * width + x]``.
    """

    def __init__(self, width: int = 256, height: int = 256) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        self.width: int = width
        self.height: int = height
        self._tiles: list[Tile] = [
            Tile(x=x, y=y) for y in range(height) for x in range(width)
        ]
        self._districts: list[District] = []

    # -- Tile access --------------------------------------------------------

    def _index(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"Tile ({x}, {y}) out of bounds (map is {self.width}x{self.height})")
        return y * self.width + x

    def get_tile(self, x: int, y: int) -> Tile:
        return self._tiles[self._index(x, y)]

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        """Replace the tile at ``(x, y)`` with *tile*."""
        self._tiles[self._index(x, y)] = tile

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    # -- Spatial queries ----------------------------------------------------

    def get_tiles_in_radius(self, cx: int, cy: int, radius: int) -> list[Tile]:
        """Return all tiles whose Chebyshev distance from ``(cx, cy)`` <= *radius*."""
        results: list[Tile] = []
        r = max(0, radius)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                nx, ny = cx + dx, cy + dy
                if self.in_bounds(nx, ny):
                    results.append(self.get_tile(nx, ny))
        return results

    def get_tiles_by_zone(self, zone: str) -> list[Tile]:
        return [t for t in self._tiles if t.zone == zone]

    # -- District management ------------------------------------------------

    def add_district(self, district: District) -> None:
        self._districts.append(district)

    @property
    def districts(self) -> list[District]:
        return list(self._districts)

    def get_district(self, x: int, y: int) -> District | None:
        """Return the first district that contains ``(x, y)``, or ``None``."""
        for d in self._districts:
            if d.contains(x, y):
                return d
        return None

    # -- Pathfinding (A*) ---------------------------------------------------

    def pathfind(self, from_xy: tuple[int, int], to_xy: tuple[int, int]) -> list[tuple[int, int]]:
        """Find a path from *from_xy* to *to_xy* using A*.

        Returns a list of ``(x, y)`` coordinates including start and end,
        or an empty list if no path exists.
        """
        sx, sy = from_xy
        gx, gy = to_xy

        if not (self.in_bounds(sx, sy) and self.in_bounds(gx, gy)):
            return []

        def heuristic(ax: int, ay: int) -> float:
            return math.hypot(gx - ax, gy - ay)

        def move_cost(x: int, y: int) -> float:
            tile = self.get_tile(x, y)
            base = _TERRAIN_COST.get(tile.terrain, 1.0)
            if tile.is_road:
                base *= 0.5
            return base

        # Priority queue entries: (f_score, counter, x, y)
        counter = 0
        open_set: list[tuple[float, int, int, int]] = []
        heapq.heappush(open_set, (heuristic(sx, sy), counter, sx, sy))

        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {(sx, sy): 0.0}

        # 8-directional neighbours
        _DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        while open_set:
            _, _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) == (gx, gy):
                # Reconstruct path
                path: list[tuple[int, int]] = [(gx, gy)]
                cur = (gx, gy)
                while cur in came_from:
                    cur = came_from[cur]
                    path.append(cur)
                path.reverse()
                return path

            for ddx, ddy in _DIRS:
                nx, ny = cx + ddx, cy + ddy
                if not self.in_bounds(nx, ny):
                    continue

                cost = move_cost(nx, ny)
                if cost >= 999.0:
                    continue  # impassable

                # diagonal moves cost sqrt(2) * tile cost
                if ddx != 0 and ddy != 0:
                    cost *= math.sqrt(2)

                tentative = g_score[(cx, cy)] + cost
                if tentative < g_score.get((nx, ny), math.inf):
                    came_from[(nx, ny)] = (cx, cy)
                    g_score[(nx, ny)] = tentative
                    f = tentative + heuristic(nx, ny)
                    counter += 1
                    heapq.heappush(open_set, (f, counter, nx, ny))

        return []  # no path found
