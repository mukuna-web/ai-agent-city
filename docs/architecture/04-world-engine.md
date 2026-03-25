# World & City Architecture

## Map System — Hierarchical Tile Grid

The world is a 2D grid of tiles organized into districts. Not voxel, not continuous —
discrete tiles are computationally cheap, easy to reason about, and sufficient for
economic/social simulation.

```
WORLD (256x256 tiles default, expandable)
├── DISTRICT: "Old Town" (32x32 tile region)
│   ├── ZONE: Residential
│   │   ├── TILE (4,7): House — owned by Agent #42
│   │   ├── TILE (4,8): House — vacant
│   │   └── TILE (5,7): Garden — food production
│   ├── ZONE: Commercial
│   │   ├── TILE (10,12): Bakery — Firm #8
│   │   └── TILE (10,13): General Store — Firm #12
│   └── ZONE: Public
│       ├── TILE (16,16): Town Hall
│       └── TILE (17,16): School
├── DISTRICT: "Farm Belt" (64x32 region)
│   └── ZONE: Agricultural
│       ├── TILE (80,10): Wheat Farm — Firm #3
│       └── TILE (82,10): Cattle Ranch — Firm #5
└── DISTRICT: "Industrial Park"
    └── ZONE: Industrial
        ├── TILE (120,50): Lumber Mill — Firm #15
        └── TILE (122,50): Smelter — Firm #18
```

### Tile Data Structure

```python
@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    terrain: str          # "grass" | "water" | "rock" | "forest" | "sand" | "mountain"
    zone: str             # "residential" | "commercial" | "industrial" | "agricultural"
                          # | "public" | "wilderness" | "unzoned"
    building_id: str | None
    owner_id: str | None  # Agent or firm that owns this tile
    resources: dict[str, float]  # Natural resources: {"timber": 100, "stone": 50, "iron": 20}
    fertility: float      # 0-1, affects farming output
    elevation: float      # Affects building cost, flooding risk
    is_road: bool
    is_powered: bool      # Connected to power grid
    is_watered: bool      # Connected to water supply

@dataclass(frozen=True)
class District:
    district_id: str
    name: str
    bounds: tuple[int, int, int, int]  # x1, y1, x2, y2
    zone_policy: str      # Default zoning
    tax_rate: float       # District-specific tax
    services: list[str]   # Available public services
    safety_level: float   # 0-1, affects crime/danger
    desirability: float   # 0-1, affects land prices
```

## Resource System

Resources are the foundation of the economy. Every resource is finite, extracted,
transported, consumed, and priced.

### Resource Types

```python
RESOURCES = {
    # RAW MATERIALS (extracted from tiles)
    "timber":    {"category": "raw", "weight": 5, "base_value": 2},
    "stone":     {"category": "raw", "weight": 10, "base_value": 3},
    "iron_ore":  {"category": "raw", "weight": 8, "base_value": 5},
    "clay":      {"category": "raw", "weight": 6, "base_value": 1},
    "coal":      {"category": "raw", "weight": 7, "base_value": 4},

    # AGRICULTURAL (grown on fertile tiles)
    "wheat":     {"category": "agricultural", "weight": 1, "base_value": 1, "spoil_ticks": 2000},
    "vegetables":{"category": "agricultural", "weight": 1, "base_value": 2, "spoil_ticks": 1000},
    "cotton":    {"category": "agricultural", "weight": 0.5, "base_value": 3},
    "livestock": {"category": "agricultural", "weight": 20, "base_value": 15},

    # PROCESSED (crafted from raw materials)
    "lumber":    {"category": "processed", "weight": 4, "base_value": 5, "recipe": {"timber": 2}},
    "bricks":    {"category": "processed", "weight": 8, "base_value": 4, "recipe": {"clay": 3, "coal": 1}},
    "iron":      {"category": "processed", "weight": 6, "base_value": 10, "recipe": {"iron_ore": 2, "coal": 1}},
    "tools":     {"category": "processed", "weight": 2, "base_value": 15, "recipe": {"iron": 1, "timber": 1}},
    "bread":     {"category": "processed", "weight": 0.5, "base_value": 3, "recipe": {"wheat": 2}, "spoil_ticks": 500},
    "cloth":     {"category": "processed", "weight": 0.3, "base_value": 8, "recipe": {"cotton": 3}},
    "meat":      {"category": "processed", "weight": 2, "base_value": 8, "recipe": {"livestock": 1}, "spoil_ticks": 800},

    # CONSUMABLES
    "food":      {"category": "consumable", "weight": 1, "base_value": 4},  # Generic food (bread/meat/veg)
    "medicine":  {"category": "consumable", "weight": 0.1, "base_value": 20},
    "clothing":  {"category": "consumable", "weight": 0.5, "base_value": 10, "recipe": {"cloth": 2}},

    # ENERGY
    "electricity": {"category": "energy", "weight": 0, "base_value": 1},  # Produced per tick by power plants
    "water_supply": {"category": "energy", "weight": 0, "base_value": 0.5},
}
```

### Resource Extraction

```python
class ResourceExtraction:
    def extract(self, tile: Tile, worker_skill: float, tool_quality: float) -> dict[str, float]:
        """Extract resources from a tile. Depletes tile resources over time."""
        output = {}
        for resource, amount in tile.resources.items():
            if amount <= 0:
                continue
            # Output = base_rate * skill * tool_bonus * fertility
            base_rate = 0.1  # Per tick
            extraction = base_rate * worker_skill * (1 + tool_quality * 0.5)
            if RESOURCES[resource]["category"] == "agricultural":
                extraction *= tile.fertility

            extracted = min(extraction, amount)
            output[resource] = extracted
            # Tile resource decreases (non-renewable deplete, agricultural regenerate)

        return output

    def regenerate(self, tile: Tile, tick: int) -> Tile:
        """Agricultural resources regenerate. Minerals don't."""
        new_resources = dict(tile.resources)
        for resource, amount in tile.resources.items():
            if RESOURCES[resource]["category"] == "agricultural":
                max_capacity = 100 * tile.fertility
                regen_rate = 0.01 * tile.fertility
                new_resources[resource] = min(amount + regen_rate, max_capacity)
        return tile._replace(resources=new_resources)
```

## Building System

Buildings are constructed on tiles, require resources and labor, take time to build,
and serve specific functions.

```python
BUILDING_TYPES = {
    "house": {
        "size": 1,              # Tiles
        "capacity": 4,          # Max residents
        "build_cost": {"lumber": 20, "bricks": 30, "tools": 5},
        "build_ticks": 500,     # Time to construct
        "maintenance_per_tick": 0.01,  # Currency
        "requires_power": False,
        "requires_water": True,
    },
    "farm": {
        "size": 4,
        "capacity": 2,          # Workers
        "build_cost": {"lumber": 10, "tools": 3},
        "build_ticks": 200,
        "output": {"wheat": 0.5, "vegetables": 0.3},  # Per tick per worker
        "requires_power": False,
        "requires_water": True,
    },
    "workshop": {
        "size": 1,
        "capacity": 4,
        "build_cost": {"lumber": 15, "bricks": 20, "iron": 5, "tools": 8},
        "build_ticks": 400,
        "recipes": ["tools", "clothing", "bread"],
        "requires_power": True,
        "requires_water": True,
    },
    "market": {
        "size": 2,
        "capacity": 6,
        "build_cost": {"lumber": 25, "bricks": 40},
        "build_ticks": 600,
        "trade_radius": 20,     # Tiles — agents within this range can trade here
        "requires_power": False,
        "requires_water": False,
    },
    "school": {
        "size": 2,
        "capacity": 20,         # Students
        "build_cost": {"lumber": 30, "bricks": 50, "tools": 10},
        "build_ticks": 800,
        "skill_boost": 0.002,   # Per tick for students
        "requires_power": True,
        "requires_water": True,
    },
    "hospital": {
        "size": 2,
        "capacity": 10,         # Patients
        "build_cost": {"lumber": 20, "bricks": 40, "iron": 10, "tools": 15},
        "build_ticks": 1000,
        "heal_rate": 0.01,      # Health restored per tick per patient
        "requires_power": True,
        "requires_water": True,
    },
    "factory": {
        "size": 4,
        "capacity": 20,
        "build_cost": {"bricks": 100, "iron": 50, "tools": 30},
        "build_ticks": 1500,
        "production_multiplier": 3.0,  # vs workshop
        "requires_power": True,
        "requires_water": True,
    },
    "power_plant": {
        "size": 4,
        "build_cost": {"bricks": 80, "iron": 40, "tools": 20},
        "build_ticks": 2000,
        "output": {"electricity": 50},  # Per tick, powers ~50 buildings
        "fuel_consumption": {"coal": 0.5},  # Per tick
        "capacity": 5,
        "requires_power": False,
        "requires_water": True,
    },
    "warehouse": {
        "size": 2,
        "build_cost": {"lumber": 30, "bricks": 20},
        "build_ticks": 400,
        "storage_capacity": 1000,  # Weight units
        "requires_power": False,
        "requires_water": False,
    },
    "road_segment": {
        "size": 1,
        "build_cost": {"stone": 5},
        "build_ticks": 50,
        "speed_bonus": 2.0,     # Movement speed multiplier
    },
    "town_hall": {
        "size": 2,
        "build_cost": {"lumber": 40, "bricks": 80, "iron": 20},
        "build_ticks": 2000,
        "governance_radius": 50,
        "capacity": 10,
        "requires_power": True,
        "requires_water": True,
    },
}

@dataclass(frozen=True)
class Building:
    building_id: str
    type: str
    tile_x: int
    tile_y: int
    owner_id: str           # Agent or firm
    condition: float        # 0-1, degrades without maintenance
    construction_progress: float  # 0-1, 1.0 = complete
    workers: tuple[str, ...]     # Agent IDs working here
    residents: tuple[str, ...]   # Agent IDs living here (for houses)
    inventory: dict[str, float]  # Stored resources
    is_operational: bool    # Has power/water if required, condition > 0.2
    built_at_tick: int
```

### Construction Process

```python
class ConstructionSystem:
    def start_construction(self, builder_agent: Agent, building_type: str,
                          tile: Tile, world: WorldState) -> Building | None:
        """Start building. Returns None if requirements not met."""
        spec = BUILDING_TYPES[building_type]

        # Check if builder has or can acquire resources
        for resource, amount in spec["build_cost"].items():
            available = self._find_resource(builder_agent, resource, world)
            if available < amount:
                return None  # Can't afford it

        # Deduct resources
        for resource, amount in spec["build_cost"].items():
            self._consume_resource(builder_agent, resource, amount, world)

        return Building(
            building_id=uuid(),
            type=building_type,
            tile_x=tile.x,
            tile_y=tile.y,
            owner_id=builder_agent.agent_id,
            condition=1.0,
            construction_progress=0.0,
            workers=(),
            residents=(),
            inventory={},
            is_operational=False,
            built_at_tick=world.current_tick,
        )

    def advance_construction(self, building: Building, workers: list[Agent],
                             tick: int) -> Building:
        """Each tick, workers advance construction."""
        if building.construction_progress >= 1.0:
            return building

        # Progress = sum of worker construction skills / build_ticks
        spec = BUILDING_TYPES[building.type]
        skill_sum = sum(
            w.skills.skills.get("construction", 0.1) for w in workers
        )
        progress_per_tick = skill_sum / spec["build_ticks"]

        new_progress = min(building.construction_progress + progress_per_tick, 1.0)
        is_complete = new_progress >= 1.0

        return building._replace(
            construction_progress=new_progress,
            is_operational=is_complete,
        )
```

## Infrastructure Systems

### Power Grid

```python
class PowerGrid:
    """Tracks power production and consumption per district."""

    def update(self, world: WorldState) -> dict[str, float]:
        """Returns power balance per district."""
        balances = {}
        for district in world.districts:
            production = sum(
                BUILDING_TYPES[b.type].get("output", {}).get("electricity", 0)
                for b in world.get_buildings_in_district(district.district_id)
                if b.type == "power_plant" and b.is_operational
            )
            consumption = sum(
                1 for b in world.get_buildings_in_district(district.district_id)
                if BUILDING_TYPES[b.type].get("requires_power", False) and b.is_operational
            )
            balances[district.district_id] = production - consumption
        return balances
        # Buildings in districts with negative balance lose is_powered status
```

### Transportation / Logistics

```python
class LogisticsSystem:
    """Movement and goods transport."""

    def calculate_travel_time(self, from_tile: tuple[int, int],
                              to_tile: tuple[int, int],
                              world: WorldState) -> int:
        """Ticks to travel between two tiles using A* pathfinding."""
        path = self._astar(from_tile, to_tile, world)
        time = 0
        for tile_pos in path:
            tile = world.get_tile(*tile_pos)
            base_cost = 1  # 1 tick per tile
            if tile.is_road:
                base_cost = 0.5  # Roads are faster
            if tile.terrain == "mountain":
                base_cost = 3
            if tile.terrain == "water":
                base_cost = 999  # Impassable without bridge
            time += base_cost
        return int(time)

    def transport_goods(self, carrier: Agent, goods: dict[str, float],
                       from_building: Building, to_building: Building,
                       world: WorldState) -> int:
        """Calculate transport time and schedule delivery."""
        travel_time = self.calculate_travel_time(
            (from_building.tile_x, from_building.tile_y),
            (to_building.tile_x, to_building.tile_y),
            world
        )
        # Carrier skill reduces time
        logistics_skill = carrier.skills.skills.get("logistics", 0.1)
        adjusted_time = int(travel_time * (1 - logistics_skill * 0.3))
        return adjusted_time
```

### Environment and Seasons

```python
class EnvironmentSystem:
    SEASON_LENGTH = 2500  # Ticks per season
    SEASONS = ["spring", "summer", "autumn", "winter"]

    def get_season(self, tick: int) -> str:
        cycle = tick % (self.SEASON_LENGTH * 4)
        season_index = cycle // self.SEASON_LENGTH
        return self.SEASONS[season_index]

    def get_modifiers(self, tick: int) -> dict:
        season = self.get_season(tick)
        return {
            "spring": {"fertility_bonus": 0.3, "construction_speed": 1.0, "food_decay_mult": 1.0},
            "summer": {"fertility_bonus": 0.5, "construction_speed": 1.2, "food_decay_mult": 1.5},
            "autumn": {"fertility_bonus": 0.1, "construction_speed": 1.0, "food_decay_mult": 1.2},
            "winter": {"fertility_bonus": -0.2, "construction_speed": 0.6, "food_decay_mult": 0.7,
                       "heating_cost": 0.5, "health_penalty": 0.001},
        }[season]

    def trigger_disaster(self, tick: int, world: WorldState) -> list[WorldEvent]:
        """Random disasters — floods, droughts, fires. Rare but impactful."""
        events = []
        if random.random() < 0.0001:  # ~1 per 10,000 ticks
            disaster_type = random.choice(["flood", "drought", "fire", "epidemic"])
            affected_district = random.choice(world.districts)
            events.append(WorldEvent(
                type="disaster",
                subtype=disaster_type,
                district_id=affected_district.district_id,
                severity=random.uniform(0.3, 1.0),
                tick=tick,
            ))
        return events
```

## Governance System

```python
@dataclass(frozen=True)
class GovernmentState:
    treasury: float                    # Public funds
    tax_rate: float                    # Income tax rate (0-0.5)
    property_tax_rate: float           # Per-tick per owned tile
    public_services: dict[str, float]  # Service → funding level
    laws: list[Law]                    # Active regulations
    leader_agent_id: str | None        # Elected or appointed
    election_tick: int | None          # Next election

@dataclass(frozen=True)
class Law:
    law_id: str
    name: str
    type: str       # "minimum_wage" | "building_code" | "trade_regulation" | "environmental"
    value: float    # The parameter (e.g., minimum wage amount)
    enacted_tick: int

class GovernanceSystem:
    def collect_taxes(self, world: WorldState) -> float:
        """Per-tick tax collection from all working agents."""
        total = 0.0
        for agent in world.get_working_agents():
            income_tax = agent.economy.wage * world.government.tax_rate
            total += income_tax
        for tile in world.get_owned_tiles():
            property_tax = world.government.property_tax_rate
            total += property_tax
        return total

    def fund_services(self, government: GovernmentState) -> GovernmentState:
        """Allocate treasury to public services."""
        budget = government.treasury * 0.1  # Spend 10% per tick cycle
        allocations = {}
        for service, priority in government.public_services.items():
            allocations[service] = budget * priority
        return government._replace(
            treasury=government.treasury - sum(allocations.values()),
            public_services=allocations,
        )

    def enforce_minimum_wage(self, world: WorldState) -> None:
        """Ensure all wages meet minimum if law exists."""
        min_wage_law = next(
            (l for l in world.government.laws if l.type == "minimum_wage"), None
        )
        if min_wage_law:
            for firm in world.get_all_firms():
                if firm.wage_offered < min_wage_law.value:
                    firm.set_wage(min_wage_law.value)  # Forced compliance
```
