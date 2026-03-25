# Agent Architecture — Complete Technical Blueprint

## Agent Entity Structure

Every agent is an ECS entity with the following components:

```python
@dataclass(frozen=True)  # Immutable — new instance on every update
class AgentIdentity:
    agent_id: str           # UUID
    name: str
    birth_tick: int
    parent_ids: tuple[str, str] | None  # Biological parents
    generation: int         # 0 = founding, 1 = first-born, etc.

@dataclass(frozen=True)
class AgentBiology:
    age_ticks: int
    lifecycle_stage: str    # "child" | "adolescent" | "adult" | "elder"
    health: float           # 0.0 (dead) to 1.0 (perfect)
    max_health: float       # Degrades with age
    fertility: float        # 0.0 to 1.0, peaks in adulthood
    is_alive: bool
    cause_of_death: str | None

@dataclass(frozen=True)
class AgentNeeds:
    """Maslow-inspired need hierarchy. Each 0.0 (desperate) to 1.0 (satisfied)."""
    food: float
    water: float
    shelter: float
    rest: float
    health: float
    safety: float
    belonging: float        # Social connection
    esteem: float           # Reputation, status
    self_actualization: float  # Personal goals

    # Decay rates per tick (configurable per profession/age)
    food_decay: float       # ~0.002 per tick = hungry in ~500 ticks
    water_decay: float
    rest_decay: float

@dataclass(frozen=True)
class AgentPersonality:
    """Big Five personality traits, fixed at birth with slight drift."""
    openness: float         # 0-1: curiosity, creativity
    conscientiousness: float # 0-1: discipline, reliability
    extraversion: float     # 0-1: sociability, energy
    agreeableness: float    # 0-1: cooperation, trust
    neuroticism: float      # 0-1: emotional volatility

    risk_tolerance: float   # Derived: openness * (1 - neuroticism)
    ambition: float         # Derived: conscientiousness * (1 - agreeableness * 0.3)

@dataclass(frozen=True)
class AgentSkills:
    """Skill vectors — improve with practice, degrade with disuse."""
    skills: dict[str, float]  # skill_name → proficiency (0.0 to 1.0)
    # Examples: "farming": 0.7, "construction": 0.3, "trading": 0.5
    # "teaching": 0.2, "medicine": 0.0, "engineering": 0.4

    experience: dict[str, int]  # skill_name → ticks practiced
    talent: dict[str, float]    # Innate aptitude multiplier (set at birth)

@dataclass(frozen=True)
class AgentEconomy:
    cash: float                  # Currency units
    assets: list[str]            # Asset IDs (buildings, land, tools)
    employer_id: str | None      # Firm or institution ID
    profession: str | None       # Current profession
    wage: float                  # Per-tick income
    daily_expenses: float        # Running average
    savings_target: float        # Goal amount
    debt: float                  # Outstanding debts
    owned_firm_id: str | None    # If entrepreneur

@dataclass(frozen=True)
class AgentSocial:
    household_id: str | None
    partner_id: str | None       # Spouse/partner
    children_ids: tuple[str, ...]
    parent_ids: tuple[str, ...]
    friends: dict[str, float]    # agent_id → friendship strength (0-1)
    trust: dict[str, float]      # agent_id → trust level (0-1)
    reputation: float            # Public reputation (0-1)
    social_class: str            # "lower" | "middle" | "upper" (derived)

@dataclass(frozen=True)
class AgentGoals:
    """Adaptive goal system. Goals re-evaluated at Tier 1 frequency."""
    immediate: list[Goal]        # This tick: eat, go to work, sleep
    short_term: list[Goal]       # Next ~100 ticks: earn money, fix house
    long_term: list[Goal]        # Next ~10000 ticks: buy house, have child, career
    active_plan: Plan | None     # Current executing plan

@dataclass(frozen=True)
class Goal:
    goal_id: str
    type: str                    # "satisfy_need" | "economic" | "social" | "personal"
    description: str
    target_condition: str        # Evaluatable condition
    priority: float              # 0-1
    deadline_tick: int | None
    progress: float              # 0-1

@dataclass(frozen=True)
class Plan:
    plan_id: str
    goal_id: str
    steps: tuple[PlanStep, ...]
    current_step: int
    status: str                  # "executing" | "blocked" | "completed" | "failed"

@dataclass(frozen=True)
class PlanStep:
    action: str                  # "move_to" | "work" | "buy" | "sell" | "talk" | "build" | "rest"
    target: str                  # Entity or location ID
    parameters: dict
    estimated_ticks: int
```

## Agent Memory System

### Three-Tier Memory Architecture

```
┌─────────────────────────────────┐
│     WORKING MEMORY (Tier 0)     │
│  Current state, active plan,    │
│  immediate perceptions          │
│  Size: ~20 items                │
│  Persistence: current tick only │
├─────────────────────────────────┤
│    EPISODIC MEMORY (Tier 1)     │
│  Recent events experienced      │
│  Stored as: (tick, event, loc,  │
│    agents_involved, emotion)    │
│  Size: last 500 events          │
│  Compressed: older → summary    │
│  Storage: vector DB (HNSW)      │
├─────────────────────────────────┤
│    SEMANTIC MEMORY (Tier 2)     │
│  Learned facts about world      │
│  "Baker sells bread for $3"     │
│  "Market is north of square"    │
│  "Dr. Smith is a good doctor"   │
│  Stored as: knowledge graph     │
│  Size: ~1000 facts, pruned      │
├─────────────────────────────────┤
│   PROCEDURAL MEMORY (Tier 3)    │
│  How to do things               │
│  Skill → action sequences       │
│  Trained from experience        │
│  Stored as: policy weights      │
│  Size: one small model per      │
│  profession cluster             │
└─────────────────────────────────┘
```

### Memory Operations

```python
class AgentMemory:
    def perceive(self, event: WorldEvent) -> None:
        """Add event to working memory. Filter by relevance."""
        relevance = self._compute_relevance(event)
        if relevance > 0.3:
            self.working_memory.append(event)
            if relevance > 0.6:
                self.episodic.store(event)

    def recall(self, query: str, k: int = 5) -> list[MemoryItem]:
        """Retrieve relevant memories. Used by Tier 1+ cognition."""
        episodic_hits = self.episodic.search(query, k=k)
        semantic_hits = self.semantic.query(query, k=k)
        return self._merge_and_rank(episodic_hits, semantic_hits)

    def learn_fact(self, subject: str, predicate: str, object: str) -> None:
        """Add to semantic memory / knowledge graph."""
        self.semantic.add_triple(subject, predicate, object)

    def compress_old_memories(self, current_tick: int) -> None:
        """Periodically summarize old episodic memories."""
        old = self.episodic.get_older_than(current_tick - 5000)
        if len(old) > 100:
            summary = summarize_memories(old)  # LLM call or heuristic
            self.episodic.replace_with_summary(old, summary)

    def _compute_relevance(self, event: WorldEvent) -> float:
        """Fast relevance scoring — no LLM needed."""
        score = 0.0
        if event.involves(self.agent_id): score += 0.5
        if event.location == self.current_location: score += 0.2
        if event.type in ("danger", "opportunity", "social"): score += 0.2
        if event.involves_known_agent(self.social.friends): score += 0.1
        return min(score, 1.0)
```

## Agent Decision Loop — Tiered Cognition

```python
class AgentCognition:
    def tick(self, agent: Agent, world: WorldState, tick: int) -> list[Action]:
        """Main decision loop — called every tick."""

        # TIER 0: REACTIVE (every tick, <0.01ms)
        actions = self._reactive(agent, world)
        if actions:
            return actions  # Urgent needs override everything

        # TIER 1: DELIBERATIVE (every 10 ticks, <0.1ms)
        if tick % 10 == 0:
            self._deliberate(agent, world)

        # TIER 2: STRATEGIC (every 100 ticks, ~1ms with local model)
        if tick % 100 == 0:
            self._strategize(agent, world)

        # TIER 3: CREATIVE (on-demand, ~200ms with LLM)
        if self._needs_creative_decision(agent):
            self._create(agent, world)

        # Execute current plan
        return self._execute_plan(agent, world)

    def _reactive(self, agent: Agent, world: WorldState) -> list[Action] | None:
        """Pure symbolic — lookup tables and thresholds."""
        # Critical need satisfaction
        if agent.needs.food < 0.1:
            return [Action("find_food", priority=1.0)]
        if agent.needs.health < 0.2:
            return [Action("seek_medical", priority=0.95)]
        if agent.needs.safety < 0.2:
            return [Action("flee_danger", priority=0.99)]
        if agent.needs.rest < 0.1:
            return [Action("go_home_sleep", priority=0.9)]
        return None  # No urgent needs

    def _deliberate(self, agent: Agent, world: WorldState) -> None:
        """Evaluate goals, pick plans from known repertoire."""
        # Update need priorities
        needs_vector = agent.needs.to_vector()
        goal_priorities = self._compute_goal_priorities(needs_vector, agent.goals)

        # Select highest priority unsatisfied goal
        best_goal = max(agent.goals.all(), key=lambda g: g.priority * (1 - g.progress))

        # Find a known plan for this goal
        plan = self._select_plan(best_goal, agent.skills, world)
        if plan:
            agent = agent.with_active_plan(plan)

    def _strategize(self, agent: Agent, world: WorldState) -> None:
        """Use small local model for medium-term reasoning."""
        # Batch inference — collect all agents needing Tier 2 this tick
        # Send to local inference server
        context = self._build_strategy_context(agent, world)
        # This goes to a small (1-3B param) model
        decision = local_inference(
            prompt=f"Agent {agent.identity.name} (profession: {agent.economy.profession}, "
                   f"cash: {agent.economy.cash}, goals: {agent.goals.long_term}). "
                   f"Current situation: {context}. "
                   f"What should they focus on for the next period?",
            max_tokens=50
        )
        self._apply_strategic_decision(agent, decision)

    def _create(self, agent: Agent, world: WorldState) -> None:
        """Full LLM call for novel/complex decisions. RARE."""
        memories = agent.memory.recall(query=self._current_dilemma, k=10)
        social_context = self._get_social_context(agent, world)

        response = llm_inference(
            system="You are an autonomous agent in a city simulation.",
            prompt=self._build_creative_prompt(agent, memories, social_context),
            max_tokens=200
        )
        self._parse_and_apply_creative_decision(agent, response)

    def _needs_creative_decision(self, agent: Agent) -> bool:
        """Detect when routine cognition is insufficient."""
        return (
            agent.goals.active_plan is None and
            agent.goals.immediate == [] and
            agent.needs.min() > 0.3  # Not in crisis
        ) or (
            self._encountered_novel_situation(agent)
        ) or (
            self._social_interaction_pending(agent)
        )
```

## Agent Communication Layer

```python
class AgentCommunication:
    """Agents communicate through direct interaction and market signals."""

    def speak(self, speaker: Agent, listener: Agent, intent: str,
              content: str) -> ConversationResult:
        """Direct agent-to-agent communication."""
        # Only use LLM for actual conversation content
        # Intent is symbolic: "negotiate_wage", "propose_trade", "ask_direction",
        # "social_chat", "propose_partnership", "teach_skill"

        if intent in ("negotiate_wage", "propose_trade"):
            # Symbolic negotiation — no LLM needed
            return self._symbolic_negotiate(speaker, listener, intent, content)

        if intent == "teach_skill":
            return self._skill_transfer(speaker, listener, content)

        # Social interaction — use LLM for rich dialogue
        return self._llm_conversation(speaker, listener, intent, content)

    def broadcast(self, speaker: Agent, message: str, radius: float) -> None:
        """Announce to nearby agents (town crier, market calls)."""
        nearby = self.world.get_agents_in_radius(speaker.position, radius)
        for agent in nearby:
            agent.memory.perceive(SpeechEvent(speaker.id, message))

    def _symbolic_negotiate(self, buyer, seller, intent, content):
        """Fast negotiation using utility functions, no LLM."""
        if intent == "negotiate_wage":
            buyer_max = buyer.economy.cash * 0.3  # Max willing to pay
            seller_min = seller.needs.min_acceptable_wage()
            if buyer_max >= seller_min:
                agreed = (buyer_max + seller_min) / 2
                return NegotiationResult(agreed=True, wage=agreed)
            return NegotiationResult(agreed=False)
```

## Reproduction & Kinship Logic

```python
class ReproductionSystem:
    """Endogenous population dynamics."""

    def evaluate_reproduction(self, agent: Agent, partner: Agent,
                              world: WorldState) -> bool:
        """Should this couple have a child? Symbolic decision."""
        if agent.biology.lifecycle_stage != "adult": return False
        if partner.biology.lifecycle_stage != "adult": return False
        if agent.biology.fertility < 0.3: return False

        # Economic conditions
        household_income = agent.economy.wage + partner.economy.wage
        housing_has_space = self._check_housing_capacity(agent.social.household_id)
        can_afford = household_income > world.economy.poverty_line * 2

        # Social conditions
        relationship_quality = agent.social.trust.get(partner.agent_id, 0)
        existing_children = len(agent.social.children_ids)

        # Personality influence
        desire = (
            agent.personality.agreeableness * 0.3 +  # Cooperativeness
            (1 - agent.personality.neuroticism) * 0.2 +  # Stability
            (1 if existing_children < 2 else 0.3) * 0.3 +  # Diminishing desire
            (1 if can_afford else 0.2) * 0.2  # Economic readiness
        )

        return (
            housing_has_space and
            relationship_quality > 0.6 and
            desire > 0.5 and
            random.random() < agent.biology.fertility * 0.1  # Chance per eval
        )

    def create_child(self, parent_a: Agent, parent_b: Agent) -> Agent:
        """Spawn new agent with inherited + random traits."""
        personality = AgentPersonality(
            openness=_inherit_trait(parent_a.personality.openness,
                                   parent_b.personality.openness),
            conscientiousness=_inherit_trait(parent_a.personality.conscientiousness,
                                            parent_b.personality.conscientiousness),
            extraversion=_inherit_trait(parent_a.personality.extraversion,
                                       parent_b.personality.extraversion),
            agreeableness=_inherit_trait(parent_a.personality.agreeableness,
                                        parent_b.personality.agreeableness),
            neuroticism=_inherit_trait(parent_a.personality.neuroticism,
                                      parent_b.personality.neuroticism),
        )

        # Skill talents — genetic + random
        talents = {}
        for skill in ALL_SKILLS:
            parent_avg = (parent_a.skills.talent.get(skill, 0.5) +
                         parent_b.skills.talent.get(skill, 0.5)) / 2
            talents[skill] = clamp(parent_avg + random.gauss(0, 0.15), 0.1, 1.0)

        return Agent(
            identity=AgentIdentity(
                agent_id=uuid(),
                name=generate_name(),
                birth_tick=current_tick,
                parent_ids=(parent_a.agent_id, parent_b.agent_id),
                generation=max(parent_a.identity.generation,
                              parent_b.identity.generation) + 1,
            ),
            biology=AgentBiology(age_ticks=0, lifecycle_stage="child", health=1.0, ...),
            needs=AgentNeeds(food=1.0, water=1.0, ...),  # Born satisfied
            personality=personality,
            skills=AgentSkills(skills={}, experience={}, talent=talents),
            economy=AgentEconomy(cash=0, ...),
            social=AgentSocial(
                household_id=parent_a.social.household_id,
                parent_ids=(parent_a.agent_id, parent_b.agent_id),
                ...
            ),
        )

def _inherit_trait(a: float, b: float) -> float:
    """Midpoint of parents + gaussian noise."""
    return clamp((a + b) / 2 + random.gauss(0, 0.1), 0.0, 1.0)
```

## Agent Lifecycle Stages

```
CHILD (0 - 2000 ticks)
  - Cannot work
  - Depends on parents for all needs
  - Absorbs skills passively from household environment
  - Skill talent multipliers revealed gradually

ADOLESCENT (2000 - 4000 ticks)
  - Can attend school/apprenticeship
  - Begins skill training
  - Starts forming social connections outside family
  - Cannot reproduce

ADULT (4000 - 16000 ticks)
  - Full economic participation
  - Can work, trade, own property, start firms
  - Can reproduce (fertility peaks at 6000-8000, declines after)
  - Makes all independent decisions

ELDER (16000+ ticks)
  - Health declines (max_health decreases each tick)
  - Can still work but productivity reduced
  - Can teach (knowledge transfer bonus)
  - Death probability increases with age
  - Wealth/knowledge inheritance on death
```
