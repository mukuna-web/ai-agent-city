# Architecture Comparison & Final Decision

## Architectural Options Evaluated

### Option 1: Pure LLM-Agent Simulation

Every agent decision goes through an LLM. Like Smallville/Generative Agents.

| Dimension | Assessment |
|-----------|-----------|
| Realism | High — rich reasoning, natural language planning |
| Cost | **Catastrophic** — 500 agents × 10 decisions/tick × 100 tokens = 500K tokens/tick. Even at 1 tick/min = 720M tokens/day |
| Local feasibility | Impossible at scale. A 3B model on RTX 4090 does ~80 tok/s. 500 agents waiting in queue = minutes per tick |
| Scalability | Tops out at ~20-50 agents on local hardware |
| Learning | No real learning — just prompt engineering |
| MVP speed | Fast for <20 agents, unusable beyond that |

**Verdict: REJECTED for primary architecture. Used only for rare high-stakes decisions.**

### Option 2: Hybrid Symbolic + LLM Agents (SELECTED)

Most behavior driven by fast symbolic rules and learned policies. LLM used only for:
- Novel situations (never seen before)
- Social interaction / negotiation
- Long-term planning (periodic, not every tick)
- Creative decisions (start a business, propose marriage)

| Dimension | Assessment |
|-----------|-----------|
| Realism | High — symbolic handles routine, LLM handles novelty |
| Cost | Low — 95% of decisions are sub-millisecond symbolic lookups |
| Local feasibility | **Excellent** — LLM called maybe 50-200 times/minute total, not per agent |
| Scalability | 10K+ agents feasible |
| Learning | Symbolic rules can be trained/updated from LLM traces |
| MVP speed | Medium — need both rule engine and LLM integration |

**Verdict: SELECTED as primary architecture.**

### Option 3: Cognitive Architecture (BDI / SOAR-like)

Formal Beliefs-Desires-Intentions architecture with planner/memory/skill modules.

| Dimension | Assessment |
|-----------|-----------|
| Realism | Medium-High — structured but potentially rigid |
| Cost | Low compute, high development cost |
| Local feasibility | Excellent — no LLM needed for basic operation |
| Scalability | Excellent |
| Learning | Moderate — requires hand-designed learning rules |
| MVP speed | Slow — heavy upfront architecture investment |

**Verdict: INCORPORATED — BDI concepts (needs, goals, plans) used within hybrid design.**

### Option 4: Event-Driven Simulation + Periodic Agent Cognition (SELECTED)

World runs as discrete-event simulation. Agents don't think continuously — they
think when events demand it (hunger, job offer, social encounter, danger).

| Dimension | Assessment |
|-----------|-----------|
| Realism | High — humans don't think continuously either |
| Cost | Optimal — compute proportional to activity, not population |
| Local feasibility | Excellent |
| Scalability | **Best** — idle agents cost zero compute |
| Learning | Compatible with any learning approach |
| MVP speed | Fast — event-driven is natural for simulations |

**Verdict: SELECTED as simulation execution model.**

### Option 5: Full Continuous Agent Loops

Every agent runs a continuous decision loop every tick.

**Verdict: REJECTED — O(N) per tick regardless of activity. Wasteful at scale.**

### Option 6: Centralized World Engine vs Decentralized World Shards

| Approach | Pros | Cons |
|----------|------|------|
| Centralized | Simple, consistent, easy to debug | Single-threaded bottleneck at scale |
| Sharded | Parallel, scalable | Complex cross-shard interactions |

**Verdict: Centralized for MVP (simple). Shard by district for scale (10K+ agents).**

### Option 7: Fixed Professions vs Emergent Labor Markets

| Approach | Pros | Cons |
|----------|------|------|
| Fixed | Simple, predictable | Unrealistic, no adaptation |
| Emergent | Realistic, adaptive | Can collapse if economy breaks |

**Verdict: Emergent with guardrails. Agents choose professions based on needs/skills/market signals. Essential professions have NPC fallbacks if no agent fills them.**

### Option 8: Scripted Reproduction vs Endogenous Family Systems

| Approach | Pros | Cons |
|----------|------|------|
| Scripted | Predictable demographics | Cosmetic, not emergent |
| Endogenous | Realistic population dynamics | Can lead to extinction or explosion |

**Verdict: Endogenous with demographic regulators. Agents decide to reproduce based on resources, relationship quality, housing. Population caps and minimum floors prevent collapse.**

### Option 9: Static Intelligence vs Lifelong Learning on Local GPU

| Approach | Pros | Cons |
|----------|------|------|
| Static prompts | Simple, no training needed | Agents never improve, repetitive |
| Lifelong learning | Realistic skill growth, emergent expertise | GPU cost, training complexity |

**Verdict: Hybrid — symbolic skill levels increase with practice (fast). Periodic policy distillation from LLM traces (slow, background). Full RL reserved for post-MVP.**

---

## Final Architecture Decision

### ADR-001: Hybrid Event-Driven Simulation with Tiered Cognition

```
┌──────────────────────────────────────────────────────┐
│                  SIMULATION ENGINE                     │
│  Discrete-event world simulation (Rust/Python core)   │
│  Entity-Component-System for world state               │
│  Event bus for all state changes                       │
├──────────────────────────────────────────────────────┤
│              AGENT COGNITION TIERS                     │
│                                                        │
│  Tier 0: REACTIVE (every tick)                        │
│    - Need satisfaction (eat, sleep, move)              │
│    - Stimulus response (danger → flee)                │
│    - Routine work execution                           │
│    - Cost: ~0.01ms per agent                          │
│                                                        │
│  Tier 1: DELIBERATIVE (every ~10 ticks)               │
│    - Goal evaluation                                  │
│    - Plan selection from known plans                  │
│    - Social interaction decisions                     │
│    - Resource allocation                              │
│    - Cost: ~0.1ms per agent                           │
│                                                        │
│  Tier 2: STRATEGIC (every ~100 ticks)                 │
│    - Long-term goal revision                          │
│    - Career planning                                  │
│    - Relationship evaluation                          │
│    - Cost: ~1ms per agent (local inference)            │
│                                                        │
│  Tier 3: CREATIVE (on-demand, rare)                   │
│    - Novel situation handling                         │
│    - Complex negotiation                              │
│    - Life decisions (marriage, career change, move)   │
│    - Cost: ~50-500ms per call (LLM inference)         │
│    - Budget: max ~200 LLM calls per simulation minute │
│                                                        │
├──────────────────────────────────────────────────────┤
│                WORLD ENGINE (ECS)                      │
│  Entities: agents, buildings, resources, items         │
│  Components: position, inventory, health, skills       │
│  Systems: physics, economy, social, construction       │
├──────────────────────────────────────────────────────┤
│              ECONOMIC ENGINE                           │
│  Double-entry bookkeeping                             │
│  Order-book markets for commodities                   │
│  Labor market with wage discovery                     │
│  Firm accounting with P&L                             │
├──────────────────────────────────────────────────────┤
│              PERSISTENCE + LEARNING                    │
│  SQLite/DuckDB for world state snapshots              │
│  Vector DB for agent episodic memory                  │
│  Periodic policy distillation on local GPU            │
└──────────────────────────────────────────────────────┘
```

### Why This Architecture Wins

1. **500 agents at 10 ticks/sec on a single machine** — Tier 0/1 are pure arithmetic.
   Only ~50-100 Tier 2 calls per second (batched local inference). Maybe 3-5 Tier 3
   LLM calls per second.

2. **Emergent yet stable** — Symbolic rules provide economic laws of motion. LLM
   provides creativity and novelty. Neither dominates.

3. **Falsifiable** — Economic subsystem produces real prices, wages, employment rates.
   You can graph them and verify they behave like real economics.

4. **Scalable** — Event-driven means idle agents cost nothing. Shard by district for 10K+.

5. **Buildable** — MVP is a simulation engine + symbolic agents + periodic LLM.
   Learning and advanced cognition added incrementally.
