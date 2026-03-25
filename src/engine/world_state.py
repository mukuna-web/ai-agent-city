"""Central world state container — the single source of truth."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    """
    Mutable world state container. Updated each tick by simulation systems.

    Design note: While individual entities (Agent, Building, Tile) are immutable
    frozen dataclasses, the WorldState itself is mutable because it's the
    collection that gets updated each tick. Individual entities are replaced
    (not mutated) via dict reassignment.
    """

    current_tick: int = 0
    seed: int = 42

    # Entity registries — keyed by ID for O(1) lookup
    agents: dict[str, Any] = field(default_factory=dict)
    buildings: dict[str, Any] = field(default_factory=dict)
    firms: dict[str, Any] = field(default_factory=dict)
    households: dict[str, Any] = field(default_factory=dict)

    # World map (set externally after construction)
    world_map: Any = None

    # Districts
    districts: list[Any] = field(default_factory=list)

    # Economic state
    ledger: Any = None
    market: Any = None
    labor_market: Any = None
    government: Any = None

    # Metrics history
    metrics_history: list[Any] = field(default_factory=list)

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)

    # --- Agent accessors ---

    def get_agent(self, agent_id: str) -> Any | None:
        return self.agents.get(agent_id)

    def set_agent(self, agent_id: str, agent: Any) -> None:
        self.agents[agent_id] = agent

    def remove_agent(self, agent_id: str) -> Any | None:
        return self.agents.pop(agent_id, None)

    def get_all_agents(self) -> list[Any]:
        return list(self.agents.values())

    def get_alive_agents(self) -> list[Any]:
        return [a for a in self.agents.values() if a.biology.is_alive]

    def get_working_agents(self) -> list[Any]:
        return [a for a in self.agents.values()
                if a.biology.is_alive
                and a.biology.lifecycle_stage in ("adult", "elder")
                and a.economy.employer_id is not None]

    def get_agents_by_profession(self, profession: str) -> list[Any]:
        return [a for a in self.agents.values()
                if a.economy.profession == profession and a.biology.is_alive]

    # --- Building accessors ---

    def get_building(self, building_id: str) -> Any | None:
        return self.buildings.get(building_id)

    def set_building(self, building_id: str, building: Any) -> None:
        self.buildings[building_id] = building

    def get_buildings_in_district(self, district_id: str) -> list[Any]:
        # Would need tile→district mapping; simplified for now
        return list(self.buildings.values())

    def get_buildings_by_type(self, building_type: str) -> list[Any]:
        return [b for b in self.buildings.values() if b.type == building_type]

    # --- Firm accessors ---

    def get_firm(self, firm_id: str) -> Any | None:
        return self.firms.get(firm_id)

    def set_firm(self, firm_id: str, firm: Any) -> None:
        self.firms[firm_id] = firm

    def get_all_firms(self) -> list[Any]:
        return list(self.firms.values())

    # --- Statistics ---

    def population_count(self) -> int:
        return len(self.get_alive_agents())

    def adult_count(self) -> int:
        return len([a for a in self.agents.values()
                    if a.biology.is_alive
                    and a.biology.lifecycle_stage in ("adult", "elder")])

    def child_count(self) -> int:
        return len([a for a in self.agents.values()
                    if a.biology.is_alive
                    and a.biology.lifecycle_stage in ("child", "adolescent")])
