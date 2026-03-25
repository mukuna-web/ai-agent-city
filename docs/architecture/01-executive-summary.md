# AI Agent City — Executive Summary & System Vision

## What AI Agent City Is

AI Agent City is a **persistent autonomous civilization simulator** where every resident
is an AI agent with memory, goals, needs, skills, relationships, and an economic role.
Agents don't follow scripts — they make decisions, form families, start businesses,
build infrastructure, learn from experience, and collectively grow a settlement from
primitive beginnings into a complex civilization.

The simulation runs on **local compute** using small language models and learned policy
networks, not cloud API calls. It produces emergent macro-scale phenomena (economic
cycles, class stratification, urban sprawl, labor shortages, institutional evolution)
from micro-scale agent decisions.

## What Makes It Non-Trivial

| Comparison | AI Agent City difference |
|-----------|------------------------|
| NPC simulations (Skyrim, GTA) | NPCs follow behavior trees. Our agents have real memory, adaptive goals, and economic causality. |
| Sims-like games | Sims uses scripted need satisfaction. We have emergent labor markets, price discovery, and generational knowledge transfer. |
| LLM roleplay towns (Smallville) | Smallville agents chat but don't produce real economic output. Our agents' work has causal consequences — a farmer who doesn't farm causes food scarcity. |
| Simple multi-agent sandboxes (AutoGen, CrewAI) | Those coordinate task completion. We simulate persistent lives across time with births, deaths, and civilization-scale dynamics. |
| Agent frameworks with no economy | Most frameworks lack resource scarcity, price signals, and labor markets. We treat economics as a first-class simulation substrate, not decoration. |

## Core Properties

1. **Causal Economy**: Every resource is produced, transported, consumed, and priced.
   No infinite spawning. Scarcity drives behavior.

2. **Persistent Lifecycle**: Agents are born, learn, work, age, reproduce, and die.
   Knowledge transfers across generations. Population dynamics are endogenous.

3. **Emergent Institutions**: Government, markets, schools, hospitals emerge from
   agent coordination needs, not from hardcoded game mechanics.

4. **Local Learning**: Agents improve through experience using local GPU compute —
   not just prompt engineering. Skills get better with practice.

5. **Multi-Scale Dynamics**: Individual decisions (take job, buy food, have child)
   aggregate into civilization-scale phenomena (urbanization, inequality, technological
   progress) without top-down scripting.

## Design Philosophy

- **Simulation-first, AI-second**: The world runs as a discrete-event simulation with
  real physics (resources, construction time, distance). AI provides the decision-making
  layer, not the world engine.

- **Cheap cognition, expensive actions**: Thinking (LLM inference) happens selectively.
  Most agent behavior uses fast learned policies. Full LLM reasoning triggers only for
  novel situations, social interaction, and planning.

- **Bottom-up emergence**: No global scripts for "create a market" or "start a government."
  These emerge when agents need coordination mechanisms.

- **Falsifiable economics**: The economy must produce recognizable phenomena —
  supply/demand curves, unemployment, inflation, business cycles — or the simulation
  is wrong, not "creative."
