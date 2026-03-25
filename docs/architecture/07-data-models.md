# Data Models — Database Schema Blueprint

## Design Principles

All schemas use DuckDB/SQLite-compatible SQL. Every table is designed for:
- **Append-friendly writes** — simulation ticks produce high write volume
- **Analytical reads** — dashboards, replay, and cross-entity queries
- **Immutable snapshots** — state at any tick can be reconstructed from events
- **Polymorphic flexibility** — inventories and events work across entity types

DuckDB is the primary target for its columnar storage, fast analytical queries,
and zero-config embedded deployment. SQLite is the fallback for portability.

---

## Core Entity Tables

### agents

Stores the complete state of every agent in the simulation. One row per agent,
updated each tick that changes any field. Historical state is reconstructed
from the events_log and periodic snapshots.

```sql
CREATE TABLE agents (
    agent_id            VARCHAR PRIMARY KEY,    -- UUID
    name                VARCHAR NOT NULL,
    birth_tick          INTEGER NOT NULL,
    death_tick          INTEGER,                -- NULL if alive
    generation          INTEGER NOT NULL DEFAULT 0,

    -- Biology
    age_ticks           INTEGER NOT NULL DEFAULT 0,
    lifecycle_stage     VARCHAR NOT NULL DEFAULT 'child',
                        -- CHECK (lifecycle_stage IN ('child','adolescent','adult','elder'))
    health              REAL NOT NULL DEFAULT 1.0,
    max_health          REAL NOT NULL DEFAULT 1.0,
    fertility           REAL NOT NULL DEFAULT 0.0,
    is_alive            BOOLEAN NOT NULL DEFAULT TRUE,
    cause_of_death      VARCHAR,

    -- Needs (Maslow hierarchy, 0.0 = desperate, 1.0 = satisfied)
    need_food           REAL NOT NULL DEFAULT 0.8,
    need_water          REAL NOT NULL DEFAULT 0.8,
    need_shelter        REAL NOT NULL DEFAULT 0.5,
    need_rest           REAL NOT NULL DEFAULT 0.8,
    need_health         REAL NOT NULL DEFAULT 1.0,
    need_safety         REAL NOT NULL DEFAULT 0.7,
    need_belonging      REAL NOT NULL DEFAULT 0.5,
    need_esteem         REAL NOT NULL DEFAULT 0.3,
    need_self_actual    REAL NOT NULL DEFAULT 0.1,
    food_decay_rate     REAL NOT NULL DEFAULT 0.002,
    water_decay_rate    REAL NOT NULL DEFAULT 0.003,
    rest_decay_rate     REAL NOT NULL DEFAULT 0.001,

    -- Personality (Big Five, fixed at birth with slight drift)
    p_openness          REAL NOT NULL,
    p_conscientiousness REAL NOT NULL,
    p_extraversion      REAL NOT NULL,
    p_agreeableness     REAL NOT NULL,
    p_neuroticism       REAL NOT NULL,
    risk_tolerance      REAL NOT NULL,          -- Derived
    ambition            REAL NOT NULL,          -- Derived

    -- Economy
    cash                REAL NOT NULL DEFAULT 0.0,
    employer_id         VARCHAR,                -- FK → firms.firm_id
    profession          VARCHAR,
    wage                REAL NOT NULL DEFAULT 0.0,
    daily_expenses      REAL NOT NULL DEFAULT 0.0,
    savings_target      REAL NOT NULL DEFAULT 100.0,
    debt                REAL NOT NULL DEFAULT 0.0,
    owned_firm_id       VARCHAR,                -- FK → firms.firm_id

    -- Social
    household_id        VARCHAR,                -- FK → households.household_id
    partner_id          VARCHAR,                -- FK → agents.agent_id
    reputation          REAL NOT NULL DEFAULT 0.5,
    social_class        VARCHAR NOT NULL DEFAULT 'middle',
                        -- CHECK (social_class IN ('lower','middle','upper'))

    -- Location
    current_x           INTEGER NOT NULL DEFAULT 0,
    current_y           INTEGER NOT NULL DEFAULT 0,
    home_building_id    VARCHAR,                -- FK → buildings.building_id

    -- Metadata
    last_updated_tick   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_agents_alive ON agents (is_alive) WHERE is_alive = TRUE;
CREATE INDEX idx_agents_profession ON agents (profession) WHERE profession IS NOT NULL;
CREATE INDEX idx_agents_household ON agents (household_id);
CREATE INDEX idx_agents_employer ON agents (employer_id);
CREATE INDEX idx_agents_location ON agents (current_x, current_y);
CREATE INDEX idx_agents_generation ON agents (generation);
```

---

### households

A household is a group of agents sharing a dwelling and finances. Agents
within a household pool resources for rent, food, and child-rearing.

```sql
CREATE TABLE households (
    household_id        VARCHAR PRIMARY KEY,
    name                VARCHAR NOT NULL,       -- e.g., "The Smith Family"
    head_agent_id       VARCHAR NOT NULL,       -- FK → agents.agent_id
    building_id         VARCHAR,                -- FK → buildings.building_id (home)
    shared_cash         REAL NOT NULL DEFAULT 0.0,
    monthly_rent        REAL NOT NULL DEFAULT 0.0,
    formation_tick      INTEGER NOT NULL,
    dissolved_tick      INTEGER,                -- NULL if active
    member_count        INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_households_building ON households (building_id);
CREATE INDEX idx_households_active ON households (dissolved_tick) WHERE dissolved_tick IS NULL;
```

---

### firms

A firm is an economic entity that employs agents, owns buildings, produces
goods, and participates in markets. Every non-government employer is a firm.

```sql
CREATE TABLE firms (
    firm_id             VARCHAR PRIMARY KEY,
    name                VARCHAR NOT NULL,
    owner_id            VARCHAR NOT NULL,       -- FK → agents.agent_id
    firm_type           VARCHAR NOT NULL,       -- "farm","workshop","market","mine","hospital","school","tavern"
    building_id         VARCHAR,                -- FK → buildings.building_id (HQ)
    profession_type     VARCHAR NOT NULL,       -- Primary profession this firm employs

    -- Financials
    cash                REAL NOT NULL DEFAULT 0.0,
    revenue_last_cycle  REAL NOT NULL DEFAULT 0.0,
    expenses_last_cycle REAL NOT NULL DEFAULT 0.0,
    total_wages_paid    REAL NOT NULL DEFAULT 0.0,

    -- Workforce
    employee_count      INTEGER NOT NULL DEFAULT 0,
    max_employees       INTEGER NOT NULL DEFAULT 5,

    -- Production
    production_rate     REAL NOT NULL DEFAULT 1.0,
    quality_rating      REAL NOT NULL DEFAULT 0.5,

    -- Status
    founded_tick        INTEGER NOT NULL,
    closed_tick         INTEGER,                -- NULL if active
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    last_updated_tick   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_firms_owner ON firms (owner_id);
CREATE INDEX idx_firms_type ON firms (firm_type);
CREATE INDEX idx_firms_active ON firms (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_firms_building ON firms (building_id);
```

---

### buildings

Every physical structure in the city. Includes houses, workshops, farms,
infrastructure, and public buildings. Construction is a multi-tick process
that requires builder agents and raw materials.

```sql
CREATE TABLE buildings (
    building_id         VARCHAR PRIMARY KEY,
    building_type       VARCHAR NOT NULL,       -- "house","workshop","farm","market","hospital",
                                                -- "school","tavern","warehouse","town_hall","road","wall"
    tile_x              INTEGER NOT NULL,
    tile_y              INTEGER NOT NULL,
    owner_id            VARCHAR,                -- FK → agents.agent_id or firms.firm_id
    district_id         VARCHAR,                -- FK → districts.district_id

    -- Condition
    condition           REAL NOT NULL DEFAULT 1.0,  -- 0.0 = ruin, 1.0 = perfect
    max_condition       REAL NOT NULL DEFAULT 1.0,
    decay_rate          REAL NOT NULL DEFAULT 0.0001,

    -- Construction
    is_constructed      BOOLEAN NOT NULL DEFAULT FALSE,
    construction_progress REAL NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0
    construction_cost   REAL NOT NULL DEFAULT 0.0,

    -- Capacity
    max_residents       INTEGER NOT NULL DEFAULT 0,
    max_workers         INTEGER NOT NULL DEFAULT 0,
    current_residents   INTEGER NOT NULL DEFAULT 0,
    current_workers     INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    built_tick          INTEGER,                -- Tick construction completed
    destroyed_tick      INTEGER,                -- NULL if standing
    last_updated_tick   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_buildings_tile ON buildings (tile_x, tile_y);
CREATE INDEX idx_buildings_type ON buildings (building_type);
CREATE INDEX idx_buildings_owner ON buildings (owner_id);
CREATE INDEX idx_buildings_district ON buildings (district_id);
CREATE INDEX idx_buildings_constructed ON buildings (is_constructed);
```

---

### world_tiles

Every tile in the simulation grid. Stores terrain, zoning, natural resources,
ownership, and infrastructure connectivity flags.

```sql
CREATE TABLE world_tiles (
    x                   INTEGER NOT NULL,
    y                   INTEGER NOT NULL,
    terrain             VARCHAR NOT NULL DEFAULT 'grass',
                        -- "grass","water","rock","forest","sand","mountain"
    zone                VARCHAR NOT NULL DEFAULT 'unzoned',
                        -- "residential","commercial","industrial","agricultural",
                        -- "public","wilderness","unzoned"
    building_id         VARCHAR,                -- FK → buildings.building_id
    owner_id            VARCHAR,                -- FK → agents.agent_id or firms.firm_id
    district_id         VARCHAR,                -- FK → districts.district_id

    -- Natural resources (depletable)
    res_timber          REAL NOT NULL DEFAULT 0.0,
    res_stone           REAL NOT NULL DEFAULT 0.0,
    res_iron            REAL NOT NULL DEFAULT 0.0,
    res_clay            REAL NOT NULL DEFAULT 0.0,
    res_coal            REAL NOT NULL DEFAULT 0.0,

    -- Agricultural potential
    fertility           REAL NOT NULL DEFAULT 0.5,
    elevation           REAL NOT NULL DEFAULT 0.0,

    -- Infrastructure
    is_road             BOOLEAN NOT NULL DEFAULT FALSE,
    is_powered          BOOLEAN NOT NULL DEFAULT FALSE,
    is_watered          BOOLEAN NOT NULL DEFAULT FALSE,

    -- Land value (updated periodically by economy system)
    land_value          REAL NOT NULL DEFAULT 1.0,

    PRIMARY KEY (x, y)
);

CREATE INDEX idx_tiles_terrain ON world_tiles (terrain);
CREATE INDEX idx_tiles_zone ON world_tiles (zone);
CREATE INDEX idx_tiles_district ON world_tiles (district_id);
CREATE INDEX idx_tiles_building ON world_tiles (building_id) WHERE building_id IS NOT NULL;
CREATE INDEX idx_tiles_owner ON world_tiles (owner_id) WHERE owner_id IS NOT NULL;
```

---

### districts

Named regions of the city with their own zoning policy, tax rate, and
services. Districts drive land desirability and agent location preferences.

```sql
CREATE TABLE districts (
    district_id         VARCHAR PRIMARY KEY,
    name                VARCHAR NOT NULL,
    -- Bounding rectangle
    bound_x1            INTEGER NOT NULL,
    bound_y1            INTEGER NOT NULL,
    bound_x2            INTEGER NOT NULL,
    bound_y2            INTEGER NOT NULL,

    zone_policy         VARCHAR NOT NULL DEFAULT 'mixed',
    tax_rate            REAL NOT NULL DEFAULT 0.1,
    safety_level        REAL NOT NULL DEFAULT 0.7,
    desirability        REAL NOT NULL DEFAULT 0.5,

    -- Comma-separated service flags for simplicity; normalized table for production
    services            VARCHAR NOT NULL DEFAULT '',
                        -- e.g., "hospital,school,market,power,water"

    population          INTEGER NOT NULL DEFAULT 0,
    avg_land_value      REAL NOT NULL DEFAULT 1.0,

    last_updated_tick   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_districts_desirability ON districts (desirability DESC);
```

---

## Polymorphic and Relational Tables

### inventories

Polymorphic inventory table. Any entity (agent, firm, building) can own
resources. The entity_type column disambiguates FK targets.

```sql
CREATE TABLE inventories (
    entity_id           VARCHAR NOT NULL,
    entity_type         VARCHAR NOT NULL,       -- "agent","firm","building"
    resource            VARCHAR NOT NULL,       -- Resource name from RESOURCES registry
    quantity            REAL NOT NULL DEFAULT 0.0,
    max_capacity        REAL,                   -- NULL = unlimited
    spoil_tick          INTEGER,                -- Tick when this batch spoils (NULL = never)

    PRIMARY KEY (entity_id, entity_type, resource)
);

CREATE INDEX idx_inventories_entity ON inventories (entity_id, entity_type);
CREATE INDEX idx_inventories_resource ON inventories (resource);
CREATE INDEX idx_inventories_spoil ON inventories (spoil_tick) WHERE spoil_tick IS NOT NULL;
```

---

### skills

Per-agent skill tracking. Level improves with practice and degrades
with disuse. Talent is an innate multiplier set at birth.

```sql
CREATE TABLE skills (
    agent_id            VARCHAR NOT NULL,       -- FK → agents.agent_id
    skill_name          VARCHAR NOT NULL,       -- "farming","mining","construction","trading", etc.
    level               REAL NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0
    experience          INTEGER NOT NULL DEFAULT 0,  -- Total ticks practiced
    talent              REAL NOT NULL DEFAULT 1.0,   -- Innate aptitude multiplier (0.5-2.0)
    last_practiced_tick INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (agent_id, skill_name)
);

CREATE INDEX idx_skills_agent ON skills (agent_id);
CREATE INDEX idx_skills_name_level ON skills (skill_name, level DESC);
```

---

### social_graph

Directed relationship edges between agents. Each pair can have multiple
relationship types (friend, colleague, rival, family). Strength and trust
evolve based on interactions.

```sql
CREATE TABLE social_graph (
    agent_a_id          VARCHAR NOT NULL,       -- FK → agents.agent_id
    agent_b_id          VARCHAR NOT NULL,       -- FK → agents.agent_id
    relationship_type   VARCHAR NOT NULL,       -- "friend","colleague","rival","family",
                                                -- "mentor","neighbor","romantic","enemy"
    strength            REAL NOT NULL DEFAULT 0.5,  -- 0.0 to 1.0
    trust               REAL NOT NULL DEFAULT 0.5,  -- 0.0 to 1.0
    interaction_count   INTEGER NOT NULL DEFAULT 0,
    last_interaction_tick INTEGER NOT NULL DEFAULT 0,
    formed_tick         INTEGER NOT NULL,

    PRIMARY KEY (agent_a_id, agent_b_id, relationship_type)
);

CREATE INDEX idx_social_agent_a ON social_graph (agent_a_id);
CREATE INDEX idx_social_agent_b ON social_graph (agent_b_id);
CREATE INDEX idx_social_type ON social_graph (relationship_type);
CREATE INDEX idx_social_strength ON social_graph (strength DESC);
```

---

## Memory Tables

### memories_episodic

Agent episodic memories — experiences that happened at a specific time
and place. These are the raw material for agent decision-making. The
embedding_vector enables semantic similarity search via HNSW index.

```sql
CREATE TABLE memories_episodic (
    memory_id           VARCHAR PRIMARY KEY,
    agent_id            VARCHAR NOT NULL,       -- FK → agents.agent_id
    tick                INTEGER NOT NULL,
    event_type          VARCHAR NOT NULL,       -- "social","economic","danger","discovery",
                                                -- "achievement","loss","observation"
    description         VARCHAR NOT NULL,       -- Human-readable: "Bought bread from Alice at market"
    location_x          INTEGER,
    location_y          INTEGER,
    agents_involved     VARCHAR,                -- Comma-separated agent IDs (or JSON array)
    importance          REAL NOT NULL DEFAULT 0.5,  -- 0.0 to 1.0, drives retention
    emotional_valence   REAL NOT NULL DEFAULT 0.0,  -- -1.0 (negative) to 1.0 (positive)
    is_summary          BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if compressed from older memories
    embedding_vector    BLOB,                   -- Float32 array for HNSW similarity search

    created_tick        INTEGER NOT NULL,
    decay_factor        REAL NOT NULL DEFAULT 1.0   -- Decreases over time, pruned when < 0.1
);

CREATE INDEX idx_episodic_agent ON memories_episodic (agent_id);
CREATE INDEX idx_episodic_agent_tick ON memories_episodic (agent_id, tick DESC);
CREATE INDEX idx_episodic_importance ON memories_episodic (agent_id, importance DESC);
CREATE INDEX idx_episodic_type ON memories_episodic (event_type);
```

---

### memories_semantic

Agent semantic memories — learned facts about the world stored as
subject-predicate-object triples (knowledge graph). Confidence decays
if not reinforced, and conflicting facts can overwrite.

```sql
CREATE TABLE memories_semantic (
    memory_id           VARCHAR PRIMARY KEY,
    agent_id            VARCHAR NOT NULL,       -- FK → agents.agent_id
    subject             VARCHAR NOT NULL,       -- Entity or concept: "Baker Alice", "Market"
    predicate           VARCHAR NOT NULL,       -- Relationship: "sells", "is_located_at", "is_friend_of"
    object              VARCHAR NOT NULL,       -- Value: "bread for 3 credits", "north of town square"
    confidence          REAL NOT NULL DEFAULT 0.8,  -- 0.0 to 1.0, decays if not reinforced
    source_tick         INTEGER NOT NULL,       -- When this fact was learned
    last_confirmed_tick INTEGER NOT NULL,       -- Last tick this fact was verified
    source_type         VARCHAR NOT NULL DEFAULT 'observation'
                        -- "observation","told_by_agent","inference","rumor"
);

CREATE INDEX idx_semantic_agent ON memories_semantic (agent_id);
CREATE INDEX idx_semantic_subject ON memories_semantic (agent_id, subject);
CREATE INDEX idx_semantic_predicate ON memories_semantic (agent_id, predicate);
CREATE INDEX idx_semantic_confidence ON memories_semantic (agent_id, confidence DESC);
```

---

## Lineage and Events

### births_lineages

Tracks every birth event and the parent-child genealogy tree across
generations. Enables family tree visualization and genetic trait inheritance.

```sql
CREATE TABLE births_lineages (
    child_id            VARCHAR PRIMARY KEY,    -- FK → agents.agent_id
    parent_a_id         VARCHAR,                -- FK → agents.agent_id (NULL for founding agents)
    parent_b_id         VARCHAR,                -- FK → agents.agent_id (NULL for founding agents)
    birth_tick          INTEGER NOT NULL,
    generation          INTEGER NOT NULL DEFAULT 0,
    birth_location_x    INTEGER,
    birth_location_y    INTEGER,
    household_id        VARCHAR                 -- FK → households.household_id (born into)
);

CREATE INDEX idx_lineage_parents ON births_lineages (parent_a_id, parent_b_id);
CREATE INDEX idx_lineage_generation ON births_lineages (generation);
CREATE INDEX idx_lineage_tick ON births_lineages (birth_tick);
```

---

### events_log

Append-only log of every significant event in the simulation. This is the
source of truth for replay and the foundation for the persistence strategy.
The data_json field stores event-specific payload as structured JSON.

```sql
CREATE TABLE events_log (
    event_id            VARCHAR PRIMARY KEY,
    tick                INTEGER NOT NULL,
    event_type          VARCHAR NOT NULL,       -- "birth","death","hire","fire","trade","build",
                                                -- "harvest","fight","marry","divorce","elect",
                                                -- "law_passed","disaster","migration","founding"
    district_id         VARCHAR,                -- FK → districts.district_id (NULL if global)
    agent_ids           VARCHAR,                -- Comma-separated agent IDs involved
    entity_id           VARCHAR,                -- Primary entity affected (agent, firm, building)
    entity_type         VARCHAR,                -- "agent","firm","building","district","government"
    data_json           VARCHAR NOT NULL DEFAULT '{}',  -- Event-specific payload
    importance          REAL NOT NULL DEFAULT 0.5       -- For event feed filtering
);

CREATE INDEX idx_events_tick ON events_log (tick);
CREATE INDEX idx_events_type ON events_log (event_type);
CREATE INDEX idx_events_type_tick ON events_log (event_type, tick);
CREATE INDEX idx_events_district ON events_log (district_id) WHERE district_id IS NOT NULL;
CREATE INDEX idx_events_entity ON events_log (entity_id, entity_type);
```

---

## Market Tables

### market_transactions

Completed trades. Every unit of currency that changes hands for a resource
produces a row here. Used for price history, economic analysis, and GDP.

```sql
CREATE TABLE market_transactions (
    tx_id               VARCHAR PRIMARY KEY,
    tick                INTEGER NOT NULL,
    buyer_id            VARCHAR NOT NULL,       -- FK → agents.agent_id or firms.firm_id
    seller_id           VARCHAR NOT NULL,       -- FK → agents.agent_id or firms.firm_id
    resource            VARCHAR NOT NULL,
    quantity            REAL NOT NULL,
    price_per_unit      REAL NOT NULL,
    total_amount        REAL NOT NULL,          -- quantity * price_per_unit
    buyer_type          VARCHAR NOT NULL DEFAULT 'agent',   -- "agent","firm","government"
    seller_type         VARCHAR NOT NULL DEFAULT 'agent'
);

CREATE INDEX idx_tx_tick ON market_transactions (tick);
CREATE INDEX idx_tx_resource ON market_transactions (resource, tick);
CREATE INDEX idx_tx_buyer ON market_transactions (buyer_id);
CREATE INDEX idx_tx_seller ON market_transactions (seller_id);
```

---

### market_orders

Open order book. Active buy/sell orders awaiting matching. Orders expire
after ttl ticks if not filled. The matching engine processes these each tick.

```sql
CREATE TABLE market_orders (
    order_id            VARCHAR PRIMARY KEY,
    agent_id            VARCHAR NOT NULL,       -- FK → agents.agent_id or firms.firm_id
    resource            VARCHAR NOT NULL,
    side                VARCHAR NOT NULL,       -- "buy" | "sell"
    quantity            REAL NOT NULL,
    price               REAL NOT NULL,          -- Price per unit
    tick_created        INTEGER NOT NULL,
    ttl                 INTEGER NOT NULL DEFAULT 2400,  -- Expires after ~1 day
    filled_quantity     REAL NOT NULL DEFAULT 0.0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_orders_resource_side ON market_orders (resource, side, price)
    WHERE is_active = TRUE;
CREATE INDEX idx_orders_agent ON market_orders (agent_id);
CREATE INDEX idx_orders_expiry ON market_orders (tick_created, ttl)
    WHERE is_active = TRUE;
```

---

## Government and Policy

### government

Single-row table (or very few rows for multi-city). Tracks the city
treasury, tax policies, and elected leadership.

```sql
CREATE TABLE government (
    government_id       VARCHAR PRIMARY KEY DEFAULT 'city_gov',
    treasury            REAL NOT NULL DEFAULT 1000.0,
    tax_rate            REAL NOT NULL DEFAULT 0.10,     -- Income tax
    property_tax_rate   REAL NOT NULL DEFAULT 0.02,     -- Per-tick on land value
    sales_tax_rate      REAL NOT NULL DEFAULT 0.05,     -- On market transactions
    leader_id           VARCHAR,                        -- FK → agents.agent_id (elected mayor)
    election_tick       INTEGER,                        -- Next election tick
    election_interval   INTEGER NOT NULL DEFAULT 24000, -- ~10 days between elections
    last_updated_tick   INTEGER NOT NULL DEFAULT 0
);
```

---

### laws

Active legislation that modifies simulation parameters. Laws are proposed,
voted on, and enacted. Each law adjusts a specific parameter.

```sql
CREATE TABLE laws (
    law_id              VARCHAR PRIMARY KEY,
    law_type            VARCHAR NOT NULL,       -- "min_wage","max_tax","zoning_change",
                                                -- "trade_ban","subsidy","public_works"
    target              VARCHAR,                -- What it affects (resource, district, profession)
    value               VARCHAR NOT NULL,       -- The parameter value (interpreted by type)
    enacted_tick        INTEGER NOT NULL,
    repealed_tick       INTEGER,                -- NULL if active
    proposed_by         VARCHAR,                -- FK → agents.agent_id
    votes_for           INTEGER NOT NULL DEFAULT 0,
    votes_against       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_laws_type ON laws (law_type);
CREATE INDEX idx_laws_active ON laws (repealed_tick) WHERE repealed_tick IS NULL;
```

---

## Jobs and Employment

### job_postings

Open job listings from firms. Agents search these when unemployed or
seeking better employment. Postings close when filled or expired.

```sql
CREATE TABLE job_postings (
    posting_id          VARCHAR PRIMARY KEY,
    firm_id             VARCHAR NOT NULL,       -- FK → firms.firm_id
    profession          VARCHAR NOT NULL,
    wage                REAL NOT NULL,
    skill_requirement   REAL NOT NULL DEFAULT 0.0,  -- Minimum skill level
    tick_posted         INTEGER NOT NULL,
    ttl                 INTEGER NOT NULL DEFAULT 4800,  -- ~2 days
    filled              BOOLEAN NOT NULL DEFAULT FALSE,
    filled_by           VARCHAR,                -- FK → agents.agent_id
    filled_tick         INTEGER
);

CREATE INDEX idx_postings_profession ON job_postings (profession, wage DESC)
    WHERE filled = FALSE;
CREATE INDEX idx_postings_firm ON job_postings (firm_id);
CREATE INDEX idx_postings_active ON job_postings (filled, tick_posted)
    WHERE filled = FALSE;
```

---

## Aggregate Metrics

### city_metrics

Snapshot of city-wide economic indicators captured every N ticks (e.g., every
100 ticks). Powers the economy dashboard and historical trend analysis.

```sql
CREATE TABLE city_metrics (
    tick                INTEGER PRIMARY KEY,
    population          INTEGER NOT NULL,
    alive_count         INTEGER NOT NULL,
    births_this_cycle   INTEGER NOT NULL DEFAULT 0,
    deaths_this_cycle   INTEGER NOT NULL DEFAULT 0,

    -- Economy
    gdp                 REAL NOT NULL DEFAULT 0.0,      -- Total market transaction value
    unemployment_rate   REAL NOT NULL DEFAULT 0.0,      -- 0.0 to 1.0
    avg_wage            REAL NOT NULL DEFAULT 0.0,
    median_wage         REAL NOT NULL DEFAULT 0.0,
    gini                REAL NOT NULL DEFAULT 0.0,      -- 0.0 (equal) to 1.0 (max inequality)
    poverty_rate        REAL NOT NULL DEFAULT 0.0,      -- Fraction below poverty line
    total_cash_supply   REAL NOT NULL DEFAULT 0.0,

    -- Prices
    food_price_index    REAL NOT NULL DEFAULT 1.0,      -- Relative to base period
    housing_price_index REAL NOT NULL DEFAULT 1.0,
    general_price_index REAL NOT NULL DEFAULT 1.0,

    -- Social
    avg_happiness       REAL NOT NULL DEFAULT 0.5,      -- Average need satisfaction
    avg_health          REAL NOT NULL DEFAULT 0.8,
    crime_rate          REAL NOT NULL DEFAULT 0.0,

    -- Government
    treasury            REAL NOT NULL DEFAULT 0.0,
    tax_revenue_cycle   REAL NOT NULL DEFAULT 0.0,
    public_spending_cycle REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX idx_metrics_tick ON city_metrics (tick DESC);
```

---

## Persistence Strategy

### Snapshot + Event Sourcing Hybrid

The simulation uses a hybrid persistence model combining periodic snapshots
with an append-only event log. This provides both fast state recovery and
complete historical replay.

```
┌─────────────────────────────────────────────────────────┐
│                    WRITE PATH                           │
│                                                         │
│  Tick N:  Agent decides → Action executed → Event emitted│
│                                      │                  │
│                              ┌───────┴───────┐          │
│                              │  events_log   │          │
│                              │  (append-only)│          │
│                              └───────────────┘          │
│                                                         │
│  Every 1000 ticks:  Full state snapshot to disk         │
│                     (all entity tables serialized)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    READ PATH                            │
│                                                         │
│  Current state:  Read directly from entity tables       │
│  Historical:     Load nearest snapshot + replay events  │
│  Analytics:      Query city_metrics + market_transactions│
└─────────────────────────────────────────────────────────┘
```

#### Snapshot Schedule

| Trigger | Action | Storage |
|---------|--------|---------|
| Every 1000 ticks | Full DuckDB export (EXPORT DATABASE) | `snapshots/{tick}/` |
| Every 100 ticks | city_metrics row inserted | In-database |
| Every 10000 ticks | Compressed archive of snapshot + events | `archives/{tick}.tar.zst` |
| On shutdown | Emergency snapshot of all tables | `snapshots/latest/` |

#### Replay From Events

To reconstruct state at tick T:

1. Find the nearest snapshot at tick S where S <= T
2. Load the snapshot into a fresh DuckDB instance
3. Replay all events from events_log WHERE tick > S AND tick <= T
4. Apply each event to the appropriate entity table

```python
def replay_to_tick(target_tick: int, snapshot_dir: str, db_path: str) -> DuckDB:
    """Reconstruct simulation state at any historical tick."""
    db = duckdb.connect(db_path)
    db.execute(f"IMPORT DATABASE '{snapshot_dir}'")

    snapshot_tick = int(Path(snapshot_dir).name)
    events = db.execute(
        "SELECT * FROM events_log WHERE tick > ? AND tick <= ? ORDER BY tick",
        [snapshot_tick, target_tick]
    ).fetchall()

    for event in events:
        apply_event(db, event)  # Dispatches to per-event-type handler

    return db
```

#### Event Replay Handlers

Each event_type in events_log has a corresponding handler that mutates
entity tables:

| event_type | Tables Modified |
|------------|----------------|
| birth | agents (INSERT), births_lineages (INSERT), households (UPDATE) |
| death | agents (UPDATE), households (UPDATE), firms (UPDATE if owner) |
| hire | agents (UPDATE), firms (UPDATE), job_postings (UPDATE) |
| fire | agents (UPDATE), firms (UPDATE) |
| trade | market_transactions (INSERT), inventories (UPDATE x2), agents/firms (UPDATE cash) |
| build | buildings (INSERT or UPDATE), inventories (UPDATE), world_tiles (UPDATE) |
| harvest | inventories (UPDATE), world_tiles (UPDATE resources) |
| marry | agents (UPDATE x2), social_graph (INSERT), households (UPDATE) |
| elect | government (UPDATE) |
| law_passed | laws (INSERT), government (UPDATE) |
| disaster | buildings (UPDATE), agents (UPDATE), world_tiles (UPDATE) |

#### Data Retention

- **events_log**: Kept indefinitely (compressed after archiving)
- **Entity tables**: Only current state; historical via snapshots
- **memories_episodic**: Pruned per-agent when decay_factor < 0.1
- **memories_semantic**: Pruned when confidence < 0.1
- **market_orders**: Purged when is_active = FALSE and tick_created < current_tick - 10000
- **Snapshots**: Kept last 10 full snapshots; older ones archived and compressed

#### Estimated Storage (500 agents, 256x256 world)

| Table | Rows (steady state) | Row Size | Total |
|-------|---------------------|----------|-------|
| agents | 500 | ~500 B | 250 KB |
| world_tiles | 65,536 | ~100 B | 6.5 MB |
| inventories | ~5,000 | ~50 B | 250 KB |
| skills | ~2,500 | ~50 B | 125 KB |
| social_graph | ~10,000 | ~60 B | 600 KB |
| memories_episodic | ~250,000 | ~200 B | 50 MB |
| memories_semantic | ~500,000 | ~150 B | 75 MB |
| events_log | ~1M/day | ~150 B | 150 MB/day |
| market_transactions | ~50K/day | ~80 B | 4 MB/day |
| city_metrics | ~240/day | ~200 B | 48 KB/day |

Total steady-state: ~130 MB in-memory. Events log is the primary growth
driver at ~150 MB per simulation day. Archiving with zstd compression
achieves roughly 10:1 ratio on the columnar event data.
