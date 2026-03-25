# AI Agent City: MVP Implementation Plan

## MVP Goal
A runnable simulation with 20 agents in a 50x50 grid city, demonstrating learning, trading, skill growth, and emergent social behavior over 1000 ticks.

---

## Phase 1: Foundation (Week 1)

### 1.1 Project Setup
- Python 3.11+ project with `uv` or `poetry`
- Monorepo structure:
  ```
  ai-agent-city/
  ├── engine/          # Simulation engine
  │   ├── world.py     # Grid, tiles, buildings
  │   ├── clock.py     # World clock, tick system
  │   ├── engine.py    # Main simulation loop
  │   └── events.py    # Event system
  ├── agents/          # Agent system
  │   ├── agent.py     # Base agent class
  │   ├── actions.py   # Action definitions
  │   ├── personality.py # Personality traits
  │   └── inventory.py # Inventory management
  ├── learning/        # Learning system
  │   ├── learner.py   # RL-based learner
  │   ├── memory.py    # Memory architecture
  │   ├── skills.py    # Skill system
  │   └── knowledge.py # Knowledge graph
  ├── economy/         # Economy (Tejas's component)
  │   ├── market.py
  │   └── currency.py
  ├── viz/             # Visualization
  │   ├── server.py    # WebSocket server
  │   └── frontend/    # Web frontend
  ├── tests/
  ├── config.yaml      # Simulation parameters
  └── main.py          # Entry point
  ```

### 1.2 Core Data Models
- [ ] Tile, Building, Resource dataclasses
- [ ] Agent base class with position, inventory, stats
- [ ] WorldGrid with spatial queries
- [ ] WorldClock with day/night cycle

### Deliverable: Empty world that renders, clock ticks

---

## Phase 2: Agents & Actions (Week 2)

### 2.1 Agent Basics
- [ ] Agent spawning with random personalities
- [ ] Movement system (pathfinding: A* on grid)
- [ ] Action point system (5 AP per tick)
- [ ] Perception: agents see tiles within radius 3

### 2.2 Basic Actions
- [ ] Move, Gather, Rest, Communicate
- [ ] Action validation (check requirements)
- [ ] Conflict resolution (two agents, one resource)

### 2.3 Agent Personality
- [ ] Traits: curiosity, aggression, sociability, industriousness (0.0-1.0)
- [ ] Traits influence action preferences and learning rates

### Deliverable: 20 agents moving around, gathering resources

---

## Phase 3: Learning System (Week 3)

### 3.1 Core Learning
- [ ] Q-learning agent with state discretization
- [ ] Reward function: +1 gather, +2 trade, +1 rest when tired, -1 idle
- [ ] Epsilon-greedy exploration with decay

### 3.2 Memory
- [ ] Working memory (current tick context)
- [ ] Short-term memory (last 50 ticks, ring buffer)
- [ ] Long-term memory (persistent learned Q-values)

### 3.3 Skill System
- [ ] 5 starter skills: foraging, crafting, trading, building, socializing
- [ ] XP gain on practice, proficiency levels 0.0-1.0
- [ ] Skill checks: success probability = proficiency * difficulty_modifier

### Deliverable: Agents learn to prefer high-reward actions, skills improve

---

## Phase 4: Economy & Social (Week 4)

### 4.1 Trading (coordinate with Tejas)
- [ ] Barter system: agent-to-agent resource exchange
- [ ] Supply/demand pricing: prices emerge from scarcity
- [ ] Marketplace building: centralized trade location

### 4.2 Social Learning
- [ ] Agents observe neighbor success, copy strategies
- [ ] Trust network: trust grows with positive interactions
- [ ] Gossip: agents share knowledge of resource locations

### 4.3 Buildings & Jobs
- [ ] Farm, Workshop, Market, Library building types
- [ ] Agents can work at buildings for currency
- [ ] Building owners earn passive income

### Deliverable: Functioning economy, social networks forming

---

## Phase 5: Visualization & Polish (Week 5)

### 5.1 Web Dashboard
- [ ] WebSocket server streaming tick data
- [ ] HTML/Canvas grid renderer (50x50)
- [ ] Agent info panel (click to inspect)
- [ ] Real-time charts: population, avg wealth, skill distribution

### 5.2 Simulation Controls
- [ ] Play/pause/speed controls
- [ ] Save/load world state (JSON snapshots)
- [ ] Config editor: tweak parameters live

### 5.3 Analytics
- [ ] Learning curve plots per agent
- [ ] Heatmaps: agent density, resource distribution
- [ ] Economy dashboard: price history, trade volume

### Deliverable: Playable, visual simulation

---

## Phase 6: Integration & Demo (Week 6)

### 6.1 Integration with Tejas's Components
- [ ] Connect Agent Architecture (personality, goals, decision trees)
- [ ] Plug in World Engine (physics, weather, terrain generation)
- [ ] Integrate Economy system (currency, market dynamics)

### 6.2 Demo Scenarios
- [ ] "Colony Start": 20 agents, no resources, watch them build a city
- [ ] "Market Day": Pre-built city, agents trade and specialize
- [ ] "Disaster Recovery": Remove resources, watch adaptation

### 6.3 Testing & Stability
- [ ] Unit tests for all core systems
- [ ] Integration test: 1000-tick simulation completes without error
- [ ] Performance benchmark: 100 agents at <100ms per tick

---

## Tech Stack

| Component | Technology |
|---|---|
| Core Engine | Python 3.11+ |
| Data Models | dataclasses + Pydantic |
| Knowledge Graph | NetworkX (MVP) → Neo4j (scale) |
| Visualization | WebSocket + HTML Canvas |
| Config | YAML |
| Testing | pytest |
| Packaging | uv / poetry |

---

## Success Metrics (MVP)

1. Agents demonstrably learn (reward per tick increases over time)
2. Specialization emerges (agents develop different skill profiles)
3. Economy functions (prices reflect supply/demand)
4. Social networks form (trust clusters visible)
5. Simulation runs 1000 ticks with 20 agents without crashes
6. Web dashboard shows real-time city state

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Learning doesn't converge | Tune reward function, add curriculum (easy→hard) |
| Performance bottleneck | Profile early, spatial indexing, numpy vectorization |
| Integration issues with Tejas | Shared interface contracts defined in Phase 1 |
| Scope creep | Strict MVP scope, extras go to backlog |
