"""Tile data structure for the world grid."""

from __future__ import annotations

from dataclasses import dataclass, replace


TERRAIN_TYPES: tuple[str, ...] = (
    "grass",
    "water",
    "rock",
    "forest",
    "sand",
    "mountain",
)

ZONE_TYPES: tuple[str, ...] = (
    "residential",
    "commercial",
    "industrial",
    "agricultural",
    "public",
    "wilderness",
    "unzoned",
)


@dataclass(frozen=True, slots=True)
class Tile:
    """A single tile on the world grid.

    Tiles are immutable; updates return new instances via ``dataclasses.replace``.
    """

    x: int
    y: int
    terrain: str = "grass"
    zone: str = "unzoned"
    building_id: str | None = None
    owner_id: str | None = None
    resources: dict[str, float] = None  # type: ignore[assignment]
    fertility: float = 0.5
    elevation: float = 0.0
    is_road: bool = False
    is_powered: bool = False
    is_watered: bool = False

    def __post_init__(self) -> None:
        # frozen=True prevents normal assignment; use object.__setattr__
        if self.resources is None:
            object.__setattr__(self, "resources", {})
        if self.terrain not in TERRAIN_TYPES:
            raise ValueError(f"Invalid terrain: {self.terrain!r}. Must be one of {TERRAIN_TYPES}")
        if self.zone not in ZONE_TYPES:
            raise ValueError(f"Invalid zone: {self.zone!r}. Must be one of {ZONE_TYPES}")

    # Convenience helpers ---------------------------------------------------

    def with_building(self, building_id: str, owner_id: str) -> Tile:
        """Return a new tile with a building placed on it."""
        return replace(self, building_id=building_id, owner_id=owner_id)

    def with_zone(self, zone: str) -> Tile:
        return replace(self, zone=zone)

    def with_resources(self, resources: dict[str, float]) -> Tile:
        return replace(self, resources=resources)

    def with_infrastructure(
        self,
        *,
        is_road: bool | None = None,
        is_powered: bool | None = None,
        is_watered: bool | None = None,
    ) -> Tile:
        return replace(
            self,
            is_road=is_road if is_road is not None else self.is_road,
            is_powered=is_powered if is_powered is not None else self.is_powered,
            is_watered=is_watered if is_watered is not None else self.is_watered,
        )
