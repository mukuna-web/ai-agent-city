# Safety, Observability & Risk Analysis

## Safety & Control Mechanisms

### Sandboxing
```
- ALL agent actions go through ActionValidator before execution
- No agent can access real filesystem, network, or external services
- LLM inference is sandboxed — model cannot make API calls or access internet
- Agent decisions are pure functions: (state, perception) → action
- No agent can modify simulation rules or another agent's internal state directly
```

### Action Constraints
```python
class ActionValidator:
    MAX_CASH_TRANSFER_PER_TICK = 1000   # Prevent infinite money bugs
    MAX_RESOURCE_TRANSFER = 500          # Prevent resource duplication
    MAX_BUILDINGS_PER_AGENT = 10         # Prevent monopoly
    MAX_EMPLOYEES_PER_FIRM = 50          # Prevent mega-corps early

    def validate(self, action: Action, agent: Agent, world: WorldState) -> bool:
        if action.type == "transfer_cash" and action.amount > self.MAX_CASH_TRANSFER_PER_TICK:
            return False
        if action.type == "build" and len(agent.economy.assets) >= self.MAX_BUILDINGS_PER_AGENT:
            return False
        if action.type == "hire" and len(world.get_firm(agent.economy.owned_firm_id).employees) >= self.MAX_EMPLOYEES_PER_FIRM:
            return False
        # Conservation laws: total resources in ≈ total resources out
        return True
```

### Deterministic Replay
```python
class ReplaySystem:
    """Every simulation run is fully reproducible from seed + events."""
    def __init__(self, seed: int):
        self.seed = seed
        self.event_log: list[tuple[int, str, dict]] = []  # (tick, event_type, data)
        self.rng = random.Random(seed)

    def log_event(self, tick: int, event_type: str, data: dict) -> None:
        self.event_log.append((tick, event_type, data))

    def replay_from(self, start_tick: int) -> WorldState:
        """Rebuild world state by replaying events from start."""
        world = self._initial_state(self.seed)
        for tick, event_type, data in self.event_log:
            if tick >= start_tick:
                world = self._apply_event(world, tick, event_type, data)
        return world

    def branch(self, at_tick: int, new_seed: int) -> "ReplaySystem":
        """Create alternate timeline from a specific point."""
        branched = ReplaySystem(new_seed)
        branched.event_log = [(t, e, d) for t, e, d in self.event_log if t < at_tick]
        return branched
```

### Intervention Controls
```
- PAUSE: Freeze simulation at any tick
- INSPECT: View any agent's full internal state, memory, goals
- EDIT: Modify agent state manually (for debugging/research)
- INJECT: Add events manually (give agent money, trigger disaster)
- ROLLBACK: Return to any previous tick (via replay)
- BRANCH: Fork timeline at any point for A/B comparison
- SPEED: 0.1x to 100x simulation speed
```

## Observability — Inspectable Everything

### City Dashboard (main view)
```
┌──────────────────────────────────────────────────────────┐
│  🏙️ AI Agent City — Tick 45,230 | Era: Town | Season: Summer  │
├──────────────────┬──────────────────┬────────────────────┤
│  POPULATION      │  ECONOMY         │  INFRASTRUCTURE    │
│  Total: 347      │  GDP: 12,450₵    │  Buildings: 89     │
│  Adults: 201     │  Unemployment: 8%│  Roads: 156 tiles  │
│  Children: 98    │  Avg Wage: 1.2₵  │  Power: 85%        │
│  Elders: 48      │  Gini: 0.34      │  Water: 92%        │
│  Births/100t: 3  │  Inflation: 2.1% │  Housing: 78%      │
│  Deaths/100t: 1  │  Active Firms: 23│                    │
├──────────────────┴──────────────────┴────────────────────┤
│  [3D CITY VIEW]                                          │
│  Isometric view of all buildings, agents walking around  │
│  Click any agent or building to inspect                  │
├──────────────────────────────────────────────────────────┤
│  EVENT FEED                                              │
│  🔔 Alice opened "Alice's Bakery" in Old Town           │
│  🏠 Bob and Carol formed a household                     │
│  ⚠️ Food prices up 15% — farmer shortage                │
│  💀 Elder David (gen 0) died at age 18,230 ticks        │
│  🎓 Eve graduated apprenticeship → promoted to doctor    │
└──────────────────────────────────────────────────────────┘
```

### Per-Agent Debug Panel
```
┌─ AGENT: Alice (agent-a1b2c3) ──────────────────────────┐
│ Age: 6,450 ticks (adult) | Health: 0.87 | Gen: 1       │
│ Profession: Baker | Firm: Alice's Bakery | Wage: 1.5₵  │
│ Cash: 234₵ | Assets: Bakery (tile 10,12), House (4,7)  │
│ Partner: Bob | Children: Eve (child), Frank (adolescent)│
├─ NEEDS ─────────────────────────────────────────────────┤
│ Food: ████████░░ 0.82  | Rest: ██████░░░░ 0.63         │
│ Safety: █████████░ 0.91| Belonging: ████████░░ 0.78     │
├─ SKILLS ────────────────────────────────────────────────┤
│ crafting: ████████░░ 0.76 | trading: █████░░░░░ 0.52   │
│ farming: ██░░░░░░░░ 0.18 | teaching: ███░░░░░░░ 0.31   │
├─ PERSONALITY ───────────────────────────────────────────┤
│ O:0.7 C:0.8 E:0.6 A:0.7 N:0.2 (Ambitious, Reliable)   │
├─ CURRENT PLAN ──────────────────────────────────────────┤
│ Goal: Expand bakery (buy second oven)                   │
│ Step 3/5: Save 50₵ more (current: 234₵, target: 284₵)  │
├─ RECENT MEMORIES ───────────────────────────────────────┤
│ t45200: Sold 12 bread to Market at 3.2₵/ea             │
│ t45180: Bought wheat from Farmer Greg at 1.1₵/unit      │
│ t45150: Had conversation with Bob about Eve's schooling  │
│ t45100: Noticed iron prices rising — might affect tools  │
├─ SOCIAL GRAPH ──────────────────────────────────────────┤
│ Bob (partner): ████████░░ 0.85 trust: 0.92             │
│ Greg (friend): ██████░░░░ 0.62 trust: 0.71             │
│ Dr. Smith (acquaintance): ███░░░░░░░ 0.30 trust: 0.55  │
└─────────────────────────────────────────────────────────┘
```

### Economic Charts (live-updating)
- Price history per resource (line chart)
- Employment by profession (bar chart)
- Wage distribution (histogram)
- Gini coefficient over time (line)
- GDP growth rate (line)
- Supply vs demand per market (dual bar)
- Business creation/bankruptcy rate (bar)

### Population Charts
- Age distribution pyramid
- Birth/death rates over time
- Generation distribution
- Profession distribution by age
- Wealth distribution by generation

### Map Overlays (toggleable on 3D view)
- Land value heatmap
- Population density
- Crime/safety
- Power grid coverage
- Water supply coverage
- Economic activity (transactions/tick)
- Resource deposits

---

## Risk Analysis — Failure Modes & Mitigations

### 1. Fake Emergence
**Risk**: Agents appear to have emergent behavior but it's just random noise
**Severity**: HIGH
**Mitigation**:
- Statistical tests on economic indicators (do prices follow supply/demand?)
- Compare agent Gini coefficient to real-world range (0.25-0.45)
- Verify unemployment responds to labor market changes
- If indicators don't match basic economics, the simulation is broken

### 2. LLM Cost Explosion
**Risk**: Tier 3 creative calls grow unbounded as population increases
**Severity**: HIGH
**Mitigation**:
- Hard budget: max 200 LLM calls per simulation minute
- Queue with priority: critical decisions first
- Batch similar decisions (all agents choosing profession → one batch call)
- Tier 3 calls are logged and metered

### 3. Memory Bloat
**Risk**: 500 agents × 500 episodic memories × 1KB each = 250MB and growing
**Severity**: MEDIUM
**Mitigation**:
- Aggressive memory compression (summarize old events)
- Cap episodic memory at 500 entries per agent, FIFO
- Semantic memory pruned to 1000 facts
- Total memory budget: max 1GB for 500 agents

### 4. Economy Instability
**Risk**: Hyperinflation, deflationary spiral, or market collapse
**Severity**: HIGH
**Mitigation**:
- Money supply controlled: no infinite money creation
- Price floors and ceilings as emergency stabilizers (can be toggled off)
- Central bank agent that adjusts parameters if GDP drops >30%
- Log all transactions for post-mortem analysis

### 5. Profession Superficiality
**Risk**: Agents have jobs but work output doesn't actually affect the city
**Severity**: HIGH
**Mitigation**:
- EVERY profession's output is consumed by a real system
- Automated tests: disable all farmers → verify food supply drops → verify hunger increases
- Causal chain tests in CI

### 6. Reproduction Becoming Cosmetic
**Risk**: Children spawn but don't develop meaningfully
**Severity**: MEDIUM
**Mitigation**:
- Track skill inheritance across generations
- Verify generation 2 agents have different skill distributions than generation 0
- Parenting burden is real: parents spend time and money on children

### 7. Scaling Collapse
**Risk**: Works with 50 agents but breaks at 500
**Severity**: HIGH
**Mitigation**:
- Tiered cognition designed for O(1) per idle agent
- Benchmark at each phase: 50 → 100 → 250 → 500
- Profile bottlenecks continuously
- ECS data-oriented design for cache efficiency

### 8. Agents Becoming Repetitive
**Risk**: All agents converge to same behavior patterns
**Severity**: MEDIUM
**Mitigation**:
- Personality system ensures behavioral diversity
- Random talent distribution creates natural specialization
- Monitor diversity metrics: profession distribution, wealth spread, personality variance
- If diversity drops below threshold, inject random events/immigrants

### 9. Local GPU Bottlenecks
**Risk**: Inference can't keep up with agent count
**Severity**: HIGH
**Mitigation**:
- Tier 0/1 are zero-GPU (pure Python/Rust arithmetic)
- Tier 2 uses 1B model — 250 tok/s means ~250 strategic decisions/sec
- Tier 3 is budgeted and queued
- Can fall back to 100% symbolic if GPU unavailable (graceful degradation)

### 10. Simulation Becoming a Game Instead of Civilization
**Risk**: Too gamified, loses research/simulation value
**Severity**: MEDIUM
**Mitigation**:
- Economics must be falsifiable (produce real phenomena)
- No "fun" hacks — if something is unrealistic, fix the model, don't add a game mechanic
- Research mode: no UI, pure data output for analysis
- Comparison tests against known economic models (Solow growth, Phillips curve)
