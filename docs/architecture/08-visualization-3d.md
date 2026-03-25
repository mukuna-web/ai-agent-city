# 3D Visualization — Isometric City Renderer

## Visual Concept

The visualization presents the simulation as a living, breathing isometric 3D city
in the style of SimCity crossed with those viral AI-agent town renders. Every agent
is a visible character walking the streets, every building is a low-poly 3D model,
and economic activity plays out visually through particle effects, speech bubbles,
and color-coded overlays.

The goal: someone opens the browser, sees a cute miniature city humming with life,
zooms into an agent, watches them walk to work, buy bread, talk to a friend, go
home — and the viewer cannot stop watching.

### Core Visual Elements

- **Isometric 3D city grid** — tile-based world rendered in classic isometric projection
- **Agent characters** — small, stylized 3D humanoids (~12 polygons each) with profession-
  specific accessories (farmer hat, doctor coat, miner pickaxe)
- **Low-poly buildings** — charming, slightly exaggerated proportions. Houses have chimneys
  with smoke, workshops have visible activity, farms show growing crops
- **Day/night cycle** — ambient lighting shifts with simulation seasons; warm golden
  afternoons, blue-purple nights with window glow, orange autumn haze
- **Particle effects** — sparks at mines, wheat swaying on farms, smoke from chimneys,
  coins floating on trades, hearts during social bonding
- **Speech bubbles** — pop up when agents converse, showing brief text or emoji
- **Movement trails** — faint color-coded paths behind agents (blue for work commute,
  green for social visits, red for emergency, gold for trading)
- **Heat map overlays** — toggle-able layers showing economic activity density,
  population clusters, land value gradients, crime rates
- **Family trees** — interactive force-directed graphs spawned from agent focus view
- **Live dashboard** — side panel with real-time updating charts, metrics, and event feed

---

## Tech Stack

### Rendering Engine

**Three.js** is the primary renderer. It has the largest ecosystem, best documentation,
and sufficient performance for our target of 500+ agents at 60 FPS.

| Component | Technology | Purpose |
|-----------|-----------|---------|
| 3D Rendering | Three.js (r170+) | Scene graph, materials, lighting, instancing |
| UI Framework | React 19 | Dashboard panels, controls, overlays |
| State Bridge | Zustand | Shared state between React UI and Three.js scene |
| Charts | D3.js + visx | Economic dashboards, live-updating graphs |
| Graph Viz | d3-force-3d | Social network and family tree visualization |
| Real-time Data | WebSocket (native) | Simulation engine to frontend data push |
| Worker Thread | Web Worker | Parse simulation data off main thread |
| Build Tool | Vite | Fast HMR, optimized production builds |

### Why Three.js Over Babylon.js

- Smaller bundle size (~600 KB vs ~2 MB)
- Larger plugin ecosystem (troika-text, drei, postprocessing)
- Better fit for stylized/artistic rendering
- React Three Fiber provides declarative scene composition

---

## Views

### 1. City Overview

The default view. Full isometric 3D rendering of the entire city grid.

**Camera**: Orthographic, 45-degree isometric angle, zoom range 0.5x to 20x.
Pan with middle-mouse drag, zoom with scroll wheel.

**Visible elements**:
- All buildings rendered as instanced low-poly meshes, colored by type
- Agents as instanced sprite-meshes walking along roads
- Terrain tiles with subtle color variation by zone type
- Road network rendered as connected flat geometry
- District boundaries as faint dashed outlines on the ground plane
- Ambient particle systems (chimney smoke, farm dust, market bustle)

**Overlays (toggleable)**:
- Zone coloring (residential=green, commercial=blue, industrial=orange, agricultural=yellow)
- Land value heatmap (blue=low, red=high)
- Population density (transparent spheres of varying size)
- Economic activity (pulsing dots at trade locations)

### 2. Agent Focus

Click any agent in the city view to enter focus mode.

**Camera**: Follows the selected agent with a smooth orbit, slightly zoomed in.

**Visible elements**:
- Agent model enlarged with profession-specific details
- Floating stat card: name, age, profession, health bar, cash, mood
- Thought bubble showing current goal (e.g., "Going to buy bread")
- Social connections rendered as glowing lines to nearby known agents
- Recent memory feed scrolling in a side panel
- Path preview showing where the agent plans to go next (dotted line)

**Interactions**:
- Click relationships to see social graph centered on this agent
- Click employer to jump to their firm view
- Click home to jump to their building
- Timeline scrubber to replay this agent's recent history

### 3. Economy Dashboard

Full-screen overlay with live-updating economic charts.

**Panels**:

| Panel | Chart Type | Data Source |
|-------|-----------|-------------|
| GDP Over Time | Line chart | city_metrics.gdp |
| Unemployment | Area chart | city_metrics.unemployment_rate |
| Price Index | Multi-line (per resource) | market_transactions aggregated |
| Gini Coefficient | Line chart | city_metrics.gini |
| Wage Distribution | Histogram | agents.wage |
| Supply/Demand | Stacked bar per resource | market_orders aggregated |
| Trade Volume | Bar chart | market_transactions count per tick |
| Treasury | Line + area | government.treasury |

**Interactions**:
- Hover any data point to see exact values
- Click a resource name to see its full order book
- Drag to select a time range for comparison
- Toggle between linear and log scale

### 4. Social Network

3D force-directed graph of all agent relationships.

**Rendering**: d3-force-3d projected into a Three.js scene. Nodes are small
agent avatars, edges are colored by relationship type.

**Edge colors**:
- Green: friendship
- Red: romantic
- Blue: colleague/professional
- Orange: family
- Gray: acquaintance
- Black dashed: rivalry/enemy

**Interactions**:
- Click a node to see agent details
- Filter by relationship type
- Adjust force parameters (gravity, repulsion) via sliders
- Highlight clusters and cliques
- Search for an agent by name

### 5. Family Tree

Genealogy visualization across generations.

**Layout**: Top-down tree with generation 0 (founders) at the top. Each agent
is a node with their portrait, name, and lifespan. Lines connect parents to
children, with partner links as horizontal bridges.

**Colors**: Living agents are full color, deceased agents are faded/gray.
Current generation highlighted with a glow effect.

**Interactions**:
- Click any agent to see their details
- Collapse/expand branches
- Filter by lineage (show only descendants of a specific founder)
- Color-code by profession to see career inheritance patterns

### 6. Profession Heatmap

Top-down 2D view of the city grid with color intensity showing profession
concentration per tile/district.

**Mode selector**: Dropdown to pick a profession. The map recolors to show
where agents of that profession live and work.

**Data**: Aggregated from agents.profession + agents.current_x/current_y.

**Additional layers**:
- Workplace locations (where agents of this profession work)
- Commute lines (home to work paths)
- Skill level gradient (brighter = more skilled)

### 7. Timeline Scrubber

Horizontal timeline bar at the bottom of any view. Drag to replay
simulation history.

**Features**:
- Play/pause/speed controls (1x, 2x, 5x, 10x)
- Tick counter and season/day indicator
- Event markers on the timeline (births, deaths, elections, disasters)
- Click a marker to see event details
- Bookmarkable positions

**Data flow**: Loads historical state from snapshots and replays events.
The Three.js scene interpolates agent positions between ticks for smooth
animation even at high replay speeds.

### 8. Event Feed

Scrolling feed of significant simulation events. Displayed as a collapsible
side panel available in any view.

**Event format**: Timestamped cards with icon, description, and involved agents.

**Examples**:
- "Alice started a bakery in Market Square" (with bakery icon)
- "Flood hit Farm Belt — 3 farms damaged" (with warning icon)
- "Bob and Carol married" (with heart icon)
- "Election: Dave elected mayor with 62% vote" (with ballot icon)
- "Food shortage in Old Town — prices up 40%" (with alert icon)

**Filters**: By event type, district, importance level, involved agent.

---

## Performance Architecture

### Instanced Rendering

All agents share a single InstancedMesh. Position, rotation, color, and
animation frame are stored in per-instance attributes updated each frame
from a Float32Array buffer.

```
Agent Rendering Pipeline:
┌──────────────────┐
│  Simulation Data  │  500 agents × (x, y, rotation, state, profession)
│  (SharedArrayBuffer) │
└────────┬─────────┘
         │ Web Worker copies positions
         ▼
┌──────────────────┐
│  Float32Array     │  Instance attribute buffer
│  [x,y,z,r, ...]  │  500 × 4 floats = 8 KB
└────────┬─────────┘
         │ Upload to GPU once per frame
         ▼
┌──────────────────┐
│  InstancedMesh    │  1 draw call for all 500 agents
│  (Three.js)       │  Vertex shader reads per-instance data
└──────────────────┘
```

Buildings use the same instancing approach, grouped by building type
(one InstancedMesh per type, ~12 types = 12 draw calls for all buildings).

### Chunk-Based Tile Loading

The 256x256 world is divided into 16x16 tile chunks (256 chunks total).
Only chunks visible to the camera are rendered. Chunks at the edge of
the viewport are loaded asynchronously.

```
┌───┬───┬───┬───┬───┐
│   │   │   │   │   │
├───┼───┼───┼───┼───┤
│   │ V │ V │ V │   │   V = Visible (rendered)
├───┼───┼───┼───┼───┤   L = Loading (async)
│   │ V │ V │ V │   │       = Not loaded
├───┼───┼───┼───┼───┤
│   │ L │ V │ L │   │
├───┼───┼───┼───┼───┤
│   │   │   │   │   │
└───┴───┴───┴───┴───┘
```

### Level of Detail (LOD)

| Zoom Level | Agents | Buildings | Tiles | Effects |
|-----------|--------|-----------|-------|---------|
| Far (< 0.3x) | Colored dots | Flat colored squares | Solid color blocks | None |
| Medium (0.3-2x) | Billboard sprites | Simplified 3D | Textured quads | Smoke only |
| Close (2-8x) | Low-poly 3D mesh | Full 3D model | Detailed texture | All particles |
| Ultra (> 8x) | Detailed mesh + accessories | Full model + interior glow | High-res + normal map | Full VFX |

### Performance Budget

| Category | Budget | Notes |
|----------|--------|-------|
| Draw calls | < 50 | Instancing keeps this low |
| Triangles | < 500K | ~1000 per building × 200 visible + agents |
| Texture memory | < 128 MB | Atlas textures for buildings and terrain |
| JS heap | < 200 MB | State buffers + scene graph |
| Frame time | < 16.6 ms | 60 FPS target |
| WebSocket bandwidth | < 50 KB/s | Delta updates, not full state |

### Optimization Techniques

1. **Frustum culling** — Three.js built-in, skip objects outside camera view
2. **Instanced rendering** — 1 draw call per entity type regardless of count
3. **SharedArrayBuffer** — Zero-copy data sharing between Worker and main thread
4. **Object pooling** — Particle systems and speech bubbles reuse DOM/3D objects
5. **Temporal coherence** — Only update entities that moved since last frame
6. **Texture atlasing** — All building types in a single 2048x2048 atlas
7. **Deferred overlay rendering** — Heatmaps rendered to a separate canvas,
   composited via CSS, avoiding re-rendering the 3D scene

---

## Data Flow Architecture

```
┌──────────────────────────────────┐
│   Simulation Engine              │
│   (Python / Rust)                │
│                                  │
│   Tick N:                        │
│   - Agent decisions computed     │
│   - Events emitted               │
│   - State deltas calculated      │
└────────────┬─────────────────────┘
             │ WebSocket (JSON or MessagePack)
             │ Delta updates: { tick, agent_deltas[], events[], metrics }
             ▼
┌──────────────────────────────────┐
│   Web Worker                     │
│   (simulation-bridge.worker.ts)  │
│                                  │
│   - Parse incoming deltas        │
│   - Update SharedArrayBuffer     │
│   - Compute derived viz data     │
│   - Notify main thread           │
└────────────┬─────────────────────┘
             │ postMessage (minimal) + SharedArrayBuffer (bulk data)
             ▼
┌──────────────────────────────────┐
│   Main Thread                    │
│                                  │
│   ┌────────────┐ ┌────────────┐  │
│   │  Zustand    │ │  Three.js  │  │
│   │  Store      │ │  Scene     │  │
│   │            ◄──►            │  │
│   │ UI state,   │ │ Camera,    │  │
│   │ selections, │ │ Meshes,    │  │
│   │ filters     │ │ Lights,    │  │
│   │             │ │ Particles  │  │
│   └─────┬──────┘ └─────┬──────┘  │
│         │               │         │
│   ┌─────▼──────┐ ┌─────▼──────┐  │
│   │  React UI   │ │ rAF Loop   │  │
│   │  Panels     │ │ 60 FPS     │  │
│   └────────────┘ └────────────┘  │
└──────────────────────────────────┘
```

### WebSocket Protocol

Messages from simulation engine to frontend:

```typescript
// Delta update — sent every tick (or every N ticks at high speed)
interface TickUpdate {
    tick: number;
    season: 'spring' | 'summer' | 'autumn' | 'winter';
    time_of_day: number;  // 0.0 - 1.0 for lighting

    agent_deltas: AgentDelta[];   // Only agents that changed
    events: SimEvent[];           // New events this tick
    metrics: CityMetricsSnapshot; // Updated aggregate stats
}

interface AgentDelta {
    id: string;
    x: number;
    y: number;
    state: 'idle' | 'walking' | 'working' | 'talking' | 'sleeping' | 'trading';
    target_x?: number;
    target_y?: number;
    mood?: number;       // For expression changes
    speech?: string;     // Speech bubble text (null = no bubble)
}

interface SimEvent {
    type: string;
    description: string;
    agent_ids: string[];
    location?: { x: number; y: number };
    importance: number;
}
```

---

## Component Architecture

### React Component Hierarchy

```
<App>
├── <SimulationProvider>          // WebSocket connection + Zustand store
│   ├── <ViewRouter>              // Switches between views
│   │   ├── <CityView>           // View 1: Isometric 3D
│   │   │   ├── <ThreeCanvas>    // React Three Fiber canvas
│   │   │   │   ├── <IsometricCamera />
│   │   │   │   ├── <Lighting />        // Day/night cycle
│   │   │   │   ├── <TerrainChunks />   // Tile grid with LOD
│   │   │   │   ├── <BuildingInstances /> // All buildings
│   │   │   │   ├── <AgentInstances />    // All agents
│   │   │   │   ├── <ParticleManager />   // Smoke, sparks, etc.
│   │   │   │   ├── <SpeechBubbles />     // Floating text
│   │   │   │   ├── <HeatmapOverlay />    // Toggle-able layers
│   │   │   │   └── <SelectionHighlight />
│   │   │   └── <CityHUD>
│   │   │       ├── <MiniMap />
│   │   │       ├── <ToolPalette />       // Overlay toggles
│   │   │       └── <QuickStats />        // Population, tick, season
│   │   │
│   │   ├── <AgentFocusView>     // View 2: Agent details
│   │   │   ├── <ThreeCanvas>    // Reuses city scene, focused camera
│   │   │   ├── <AgentStatCard />
│   │   │   ├── <MemoryFeed />
│   │   │   ├── <GoalDisplay />
│   │   │   └── <SocialLinks />
│   │   │
│   │   ├── <EconomyDashboard>   // View 3: Charts
│   │   │   ├── <GDPChart />
│   │   │   ├── <UnemploymentChart />
│   │   │   ├── <PriceIndexChart />
│   │   │   ├── <GiniChart />
│   │   │   ├── <WageHistogram />
│   │   │   ├── <SupplyDemandBars />
│   │   │   ├── <TradeVolumeChart />
│   │   │   └── <TreasuryChart />
│   │   │
│   │   ├── <SocialNetworkView>  // View 4: Force graph
│   │   │   ├── <ForceGraph3D />
│   │   │   ├── <RelationshipFilters />
│   │   │   └── <AgentSearchBar />
│   │   │
│   │   ├── <FamilyTreeView>     // View 5: Genealogy
│   │   │   ├── <TreeLayout />
│   │   │   ├── <GenerationBands />
│   │   │   └── <LineageFilter />
│   │   │
│   │   ├── <ProfessionHeatmap>  // View 6: 2D overlay
│   │   │   ├── <ProfessionSelector />
│   │   │   ├── <HeatmapCanvas />
│   │   │   └── <CommutePaths />
│   │   │
│   │   └── <TimelineView>      // View 7: History replay
│   │       ├── <ThreeCanvas>
│   │       ├── <TimelineScrubber />
│   │       └── <EventMarkers />
│   │
│   ├── <EventFeed />            // View 8: Persistent side panel
│   ├── <TimelineBar />          // Bottom scrubber (always visible)
│   └── <ViewSwitcher />         // Navigation tabs
│
└── <ErrorBoundary />
```

### Three.js Scene Graph

```
Scene
├── AmbientLight (intensity varies with time_of_day)
├── DirectionalLight (sun — position rotates with time_of_day)
│   └── Shadow camera (covers visible chunk area)
├── HemisphereLight (sky color shifts with season)
│
├── Group: "terrain"
│   ├── Chunk_0_0 (Mesh: 16x16 merged tile geometry)
│   ├── Chunk_0_1
│   ├── Chunk_1_0
│   └── ... (only visible chunks loaded)
│
├── Group: "buildings"
│   ├── InstancedMesh: "house" (all houses, one draw call)
│   ├── InstancedMesh: "workshop"
│   ├── InstancedMesh: "farm"
│   ├── InstancedMesh: "market"
│   ├── InstancedMesh: "hospital"
│   ├── InstancedMesh: "school"
│   ├── InstancedMesh: "tavern"
│   ├── InstancedMesh: "warehouse"
│   ├── InstancedMesh: "town_hall"
│   └── InstancedMesh: "road"
│
├── Group: "agents"
│   └── InstancedMesh: "agent_body" (all agents, one draw call)
│       ├── Instance attributes: position, rotation, color, animFrame
│       └── Custom vertex shader for per-instance animation
│
├── Group: "effects"
│   ├── ParticleSystem: "chimney_smoke"
│   ├── ParticleSystem: "mine_sparks"
│   ├── ParticleSystem: "farm_dust"
│   ├── ParticleSystem: "trade_coins"
│   └── ParticleSystem: "social_hearts"
│
├── Group: "overlays"
│   ├── Mesh: "heatmap_plane" (custom shader, data texture)
│   ├── LineSegments: "district_boundaries"
│   └── LineSegments: "agent_trails" (ring buffer of positions)
│
├── Group: "ui_3d"
│   ├── Sprite[]: "speech_bubbles" (pooled, max 20 visible)
│   ├── Sprite: "selection_ring"
│   └── Line: "path_preview" (dotted line for selected agent)
│
└── Group: "post_processing"
    ├── EffectComposer
    ├── SSAOPass (subtle ambient occlusion)
    ├── UnrealBloomPass (window glow at night)
    └── SMAAPass (anti-aliasing)
```

---

## Asset Pipeline

### 3D Models

All models authored in Blender, exported as glTF 2.0 (.glb):

| Asset | Polycount | Texture | Variants |
|-------|-----------|---------|----------|
| Agent body | 120 tris | 64x64 atlas | 1 mesh, colored per-instance |
| House | 400 tris | 128x128 | 3 variants (small, medium, large) |
| Workshop | 500 tris | 128x128 | 2 variants |
| Farm | 300 tris | 128x128 | 1 base + crop overlays |
| Market | 600 tris | 128x128 | 1 variant |
| Hospital | 500 tris | 128x128 | 1 variant |
| School | 450 tris | 128x128 | 1 variant |
| Tree | 80 tris | 64x64 | 4 season variants |
| Terrain tile | 2 tris | 32x32 atlas | Per-type color |

Total asset budget: < 5 MB compressed (glb + textures).

### Loading Strategy

1. **Critical path** — terrain chunks + agent mesh loaded first (< 1 MB)
2. **Progressive** — building models loaded by visibility priority
3. **Lazy** — particle textures, post-processing shaders loaded after first render
4. **Cached** — all assets cached in IndexedDB after first load

---

## Interaction Model

### Controls

| Input | Action |
|-------|--------|
| Left click | Select agent or building |
| Right click | Context menu (inspect, follow, jump to) |
| Middle drag | Pan camera |
| Scroll | Zoom in/out |
| WASD | Pan camera (keyboard) |
| Space | Pause/resume simulation |
| 1-8 | Switch views |
| Escape | Deselect / exit focus |
| F | Follow selected agent |
| H | Toggle heatmap |
| T | Toggle trails |
| Tab | Cycle through agents |

### URL-Based State

View state is encoded in the URL for shareability:

```
/city?x=128&y=128&zoom=2.5&overlay=landvalue
/agent/agent-uuid-123?tab=memories
/economy?range=1000-5000&resource=food
/social?center=agent-uuid-456&depth=2
/family?root=agent-uuid-789
/timeline?tick=3500&speed=5
```

---

## Deployment

### Build Output

```
dist/
├── index.html          (~1 KB)
├── assets/
│   ├── app.[hash].js   (~300 KB gzip — React + Three.js + D3)
│   ├── worker.[hash].js (~15 KB gzip — Web Worker)
│   ├── models/         (~3 MB — glTF assets)
│   └── textures/       (~2 MB — atlases)
└── total: ~5.5 MB (first load, then cached)
```

### Browser Requirements

- WebGL 2.0 (98%+ of browsers)
- SharedArrayBuffer (requires COOP/COEP headers)
- WebSocket
- Web Workers
- ES2022+ (no IE11 support)

### Server Requirements

- Static file server for the frontend (any CDN)
- WebSocket endpoint from the simulation engine
- CORS headers if simulation runs on different origin
- Cross-Origin-Opener-Policy: same-origin (for SharedArrayBuffer)
- Cross-Origin-Embedder-Policy: require-corp
