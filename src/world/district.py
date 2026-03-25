"""District data structure for grouping tiles into governed regions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class District:
    """A rectangular region of the world map with its own governance policies.

    ``bounds`` is ``(x1, y1, x2, y2)`` inclusive on both ends.
    """

    district_id: str
    name: str
    bounds: tuple[int, int, int, int]
    zone_policy: str = "unzoned"
    tax_rate: float = 0.1
    services: list[str] = field(default_factory=list)
    safety_level: float = 0.5
    desirability: float = 0.5

    # Helpers ---------------------------------------------------------------

    def contains(self, x: int, y: int) -> bool:
        """Return *True* if ``(x, y)`` falls within the district bounds."""
        x1, y1, x2, y2 = self.bounds
        return x1 <= x <= x2 and y1 <= y <= y2

    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0] + 1

    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1] + 1

    @property
    def area(self) -> int:
        return self.width * self.height

    def with_tax_rate(self, rate: float) -> District:
        return replace(self, tax_rate=max(0.0, min(1.0, rate)))

    def with_safety(self, level: float) -> District:
        return replace(self, safety_level=max(0.0, min(1.0, level)))

    def with_desirability(self, level: float) -> District:
        return replace(self, desirability=max(0.0, min(1.0, level)))
