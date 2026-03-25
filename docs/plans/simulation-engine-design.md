# AI Agent City: Simulation Engine Design

## Overview
The Simulation Engine is the core runtime that drives the city forward in time, managing agent actions, world state, physics, and event resolution.

---

## 1. Engine Architecture

```
+-----------------------------------------------------------+
|                    SIMULATION ENGINE                       |
|                                                            |
|  +------------------+     +------------------+             |
|  |   World Clock    |---->|   Tick Scheduler |             |
|  |  (time manager)  |     |  (priority queue)|             |
|  +------------------+     +--------+---------+             |
|                                    |                       |
|            +----------+------------+----------+            |
|            v           v                      v            |
|  +--------+---+  +----+-------+  +-----------+--------+   |
|  | Agent      |  | Environment|  | Event               |  |
|  | Processor  |  | Manager    |  | Resolver            |  |
|  +--------+---+  +----+-------+  +-----------+--------+   |
|           |            |                      |            |
|  +--------v------------v----------------------v--------+   |
|  |                  World State                        |   |
|  |  [Grid Map] [Agent States] [Resources] [Buildings] |   |
|  +-----------------------------------------------------+  |
+-----------------------------------------------------------+
```

## 2. Core Components

### 2.1 World Clock & Tick System
```python
class WorldClock:
    def __init__(self, ticks_per_day: int = 24):
        self.tick = 0
        self.ticks_per_day = ticks_per_day

    @property
    def day(self) -> int:
        return self.tick // self.ticks_per_day

    @property
    def hour(self) -> int:
        return self.tick % self.ticks_per_day

    @property
    def is_daytime(self) -> bool:
        return 6 <= self.hour < 20

    def advance(self):
        self.tick += 1
```

- **1 tick = 1 simulated hour** (configurable)
- **24 ticks = 1 day cycle** (day/night affects agent behavior)
- **Tick budget**: each agent gets N action points per tick

### 2.2 World Grid
```python
class WorldGrid:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: dict[tuple[int,int], Tile] = {}
        self.buildings: dict[tuple[int,int], Building] = {}

    def get_neighbors(self, x: int, y: int, radius: int = 1) -> list[tuple[int,int]]:
        """Get all tiles within radius (for agent perception)."""
        neighbors = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    neighbors.append((nx, ny))
        return neighbors

class Tile:
    def __init__(self, terrain: str = "ground"):
        self.terrain = terrain  # ground, water, road, building
        self.resources: list[Resource] = []
        self.agents: list[str] = []  # agent IDs present here
```

### 2.3 Tick Scheduler (Event Loop)
```python
class SimulationEngine:
    def __init__(self, world: WorldGrid, agents: list[Agent]):
        self.world = world
        self.agents = {a.id: a for a in agents}
        self.clock = WorldClock()
        self.event_queue: list[Event] = []
        self.running = False

    def run(self, max_ticks: int = 1000):
        self.running = True
        for _ in range(max_ticks):
            if not self.running:
                break
            self.tick()

    def tick(self):
        # Phase 1: Perception — agents observe surroundings
        for agent in self.agents.values():
            agent.perceive(self.world, self.clock)

        # Phase 2: Decision — agents choose actions (via Learning System)
        actions = {}
        for agent in self.agents.values():
            actions[agent.id] = agent.decide()

        # Phase 3: Resolution — resolve conflicts, execute actions
        self.resolve_actions(actions)

        # Phase 4: Environment update — resources regen, weather, events
        self.update_environment()

        # Phase 5: Learning — agents learn from outcomes
        for agent in self.agents.values():
            agent.learn()

        # Phase 6: Advance clock
        self.clock.advance()

    def resolve_actions(self, actions: dict):
        """Resolve simultaneous actions with conflict handling."""
        # Movement: first-come-first-served for contested tiles
        # Trade: both parties must agree
        # Combat: skill checks determine outcome
        # Build: requires resources and skill check
        for agent_id, action in actions.items():
            self.execute_action(agent_id, action)

    def update_environment(self):
        """Periodic world updates."""
        if self.clock.hour == 0:  # daily reset
            self.regenerate_resources()
        self.process_random_events()
```

### 2.4 Action Types

| Action | Cost (AP) | Requirements | Effect |
|---|---|---|---|
| Move | 1 | Adjacent tile free | Change position |
| Gather | 2 | Resource on tile | Add resource to inventory |
| Trade | 1 | Adjacent agent willing | Exchange resources |
| Build | 3 | Resources + skill | Place building |
| Rest | 1 | None | Restore energy |
| Learn | 2 | Near teacher/library | Gain skill XP |
| Communicate | 1 | Adjacent agent | Share knowledge |
| Work | 2 | At workplace | Earn currency |

### 2.5 Event System
```python
@dataclass
class Event:
    type: str          # "weather", "market_crash", "new_resource", "festival"
    tick: int          # when it triggers
    duration: int      # how many ticks it lasts
    affected_area: tuple[int, int, int]  # x, y, radius
    effects: dict      # {"resource_multiplier": 0.5, "mood_modifier": -0.2}

class EventManager:
    def __init__(self):
        self.scheduled_events: list[Event] = []
        self.active_events: list[Event] = []

    def check_random_events(self, tick: int) -> list[Event]:
        events = []
        if random.random() < 0.02:  # 2% chance per tick
            events.append(self.generate_random_event(tick))
        return events
```

---

## 3. Performance Considerations

- **Agent cap**: MVP supports 50-100 agents, scalable to 1000+
- **Spatial indexing**: Grid-based lookup for O(1) neighbor queries
- **Tick batching**: Actions processed in phases to allow parallelism
- **State snapshots**: Save world state every N ticks for replay/debugging
- **Headless mode**: Engine runs without visualization for fast simulation

---

## 4. Visualization Interface (Optional)

- WebSocket output stream of tick data
- Frontend renders grid, agents, resources in real-time
- Dashboard: population stats, economy graphs, learning curves
