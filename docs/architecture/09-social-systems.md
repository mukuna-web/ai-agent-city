# Social Systems & Demographics

## Relationship System

All social relationships are stored as weighted, directed edges in a social graph.

```python
@dataclass(frozen=True)
class SocialEdge:
    from_agent: str
    to_agent: str
    relationship: str   # "friend" | "partner" | "parent" | "child" | "colleague"
                        # | "mentor" | "rival" | "neighbor"
    strength: float     # 0-1, decays without interaction
    trust: float        # 0-1, built through positive interactions, broken by betrayal
    history: tuple[SocialEvent, ...]  # Last 20 interactions
    formed_tick: int

@dataclass(frozen=True)
class SocialEvent:
    tick: int
    type: str           # "conversation" | "trade" | "help" | "conflict" | "gift" | "betrayal"
    sentiment: float    # -1 to +1
    description: str

class SocialSystem:
    """Manages all social interactions and relationship dynamics."""

    DECAY_RATE = 0.0002      # Strength decays per tick without contact
    INTERACTION_BOOST = 0.05  # Strength gained per positive interaction
    TRUST_GAIN = 0.02        # Trust gained per cooperative action
    TRUST_LOSS = 0.15        # Trust lost per betrayal/conflict

    def update_relationship(self, agent_a: str, agent_b: str,
                            event: SocialEvent, graph: dict) -> dict:
        """Update relationship based on an interaction."""
        key = (agent_a, agent_b)
        edge = graph.get(key)

        if edge is None:
            # New relationship
            edge = SocialEdge(
                from_agent=agent_a, to_agent=agent_b,
                relationship="acquaintance", strength=0.1,
                trust=0.3, history=(), formed_tick=event.tick,
            )

        new_strength = clamp(
            edge.strength + event.sentiment * self.INTERACTION_BOOST, 0, 1
        )
        new_trust = clamp(
            edge.trust + (self.TRUST_GAIN if event.sentiment > 0 else -self.TRUST_LOSS * abs(event.sentiment)),
            0, 1
        )

        # Promote relationship type based on strength
        new_type = edge.relationship
        if new_strength > 0.6 and edge.relationship == "acquaintance":
            new_type = "friend"
        if new_strength < 0.1:
            new_type = "acquaintance"

        new_edge = SocialEdge(
            from_agent=agent_a, to_agent=agent_b,
            relationship=new_type,
            strength=new_strength,
            trust=new_trust,
            history=(*edge.history[-19:], event),
            formed_tick=edge.formed_tick,
        )

        return {**graph, key: new_edge}

    def decay_all(self, graph: dict) -> dict:
        """Decay all relationships slightly each tick."""
        new_graph = {}
        for key, edge in graph.items():
            new_strength = max(0, edge.strength - self.DECAY_RATE)
            if new_strength > 0.01:  # Prune dead relationships
                new_graph[key] = edge._replace(strength=new_strength)
        return new_graph

    def find_friends(self, agent_id: str, graph: dict, min_strength: float = 0.3) -> list[str]:
        return [edge.to_agent for key, edge in graph.items()
                if edge.from_agent == agent_id and edge.strength >= min_strength]
```

## Family System

```python
@dataclass(frozen=True)
class Household:
    household_id: str
    members: tuple[str, ...]      # Agent IDs
    head_id: str                   # Primary decision maker
    building_id: str | None        # Home
    shared_cash: float             # Household finances
    formation_tick: int

class FamilySystem:
    """Partnership formation, household management, child-rearing."""

    def evaluate_partnership(self, agent_a: Agent, agent_b: Agent,
                             social_graph: dict) -> float:
        """Should these two form a partnership? Returns compatibility score."""
        edge = social_graph.get((agent_a.agent_id, agent_b.agent_id))
        if not edge or edge.strength < 0.5 or edge.trust < 0.4:
            return 0  # Not close enough

        # Compatibility factors
        personality_compat = 1 - abs(
            agent_a.personality.extraversion - agent_b.personality.extraversion
        ) * 0.3 - abs(
            agent_a.personality.agreeableness - agent_b.personality.agreeableness
        ) * 0.3

        # Economic stability
        combined_income = agent_a.economy.wage + agent_b.economy.wage
        economic_score = min(combined_income / 2.0, 1.0)

        # Age compatibility
        age_diff = abs(agent_a.biology.age_ticks - agent_b.biology.age_ticks)
        age_score = max(0, 1 - age_diff / 4000)

        return (
            edge.strength * 0.3 +
            edge.trust * 0.2 +
            personality_compat * 0.2 +
            economic_score * 0.2 +
            age_score * 0.1
        )

    def form_household(self, agent_a: Agent, agent_b: Agent) -> Household:
        """Create a new household when partnership forms."""
        return Household(
            household_id=uuid(),
            members=(agent_a.agent_id, agent_b.agent_id),
            head_id=agent_a.agent_id,
            building_id=agent_a.social.household_id,  # Move into one partner's home
            shared_cash=agent_a.economy.cash + agent_b.economy.cash,
            formation_tick=0,
        )

    def child_development(self, child: Agent, household: Household,
                          world: WorldState, tick: int) -> Agent:
        """Children develop based on household quality and parental investment."""
        parents = [world.get_agent(pid) for pid in child.social.parent_ids
                   if world.get_agent(pid)]

        # Education: is child in school?
        in_school = self._is_in_school(child, world)

        # Skill development
        new_child = child
        for parent in parents:
            if parent:
                # Passive skill inheritance
                new_child = SkillSystem().inherit_from_parent(new_child, parent)

        if in_school:
            # School accelerates skill development
            primary_skill = self._determine_aptitude(child)
            new_child = SkillSystem().practice(new_child, primary_skill, intensity=2.0)

        # Need satisfaction from household
        household_income = sum(
            world.get_agent(m).economy.wage for m in household.members
            if world.get_agent(m) and m not in child.social.parent_ids[:0]
        )
        food_security = min(household_income / 1.0, 1.0)

        # Health and growth
        if child.needs.food < 0.3:
            # Malnutrition stunts development
            new_child = new_child  # Skills grow slower

        return new_child

    def _determine_aptitude(self, child: Agent) -> str:
        """Find the child's highest talent skill."""
        if not child.skills.talent:
            return "general"
        return max(child.skills.talent, key=child.skills.talent.get)

    def _is_in_school(self, child: Agent, world: WorldState) -> bool:
        return child.biology.lifecycle_stage in ("child", "adolescent")
```

## Death and Inheritance

```python
class DeathSystem:
    BASE_DEATH_RATE = 0.00001  # Per tick for adults
    ELDER_MULTIPLIER = 5.0
    STARVATION_THRESHOLD = 0.05  # Food need below this → rapid health decline

    def check_death(self, agent: Agent, tick: int) -> bool:
        """Determine if agent dies this tick."""
        if not agent.biology.is_alive:
            return False

        death_probability = self.BASE_DEATH_RATE

        # Age factor
        if agent.biology.lifecycle_stage == "elder":
            age_beyond_elder = agent.biology.age_ticks - 16000
            death_probability *= self.ELDER_MULTIPLIER * (1 + age_beyond_elder / 5000)

        # Health factor
        if agent.biology.health < 0.2:
            death_probability *= 10

        # Starvation
        if agent.needs.food < self.STARVATION_THRESHOLD:
            death_probability *= 20

        return random.random() < death_probability

    def process_death(self, agent: Agent, world: WorldState) -> list:
        """Handle death: inheritance, task reassignment, social notifications."""
        events = []

        # Transfer wealth to partner or children
        heirs = []
        if agent.social.partner_id:
            heirs.append(agent.social.partner_id)
        heirs.extend(agent.social.children_ids)

        if heirs:
            share = agent.economy.cash / len(heirs)
            for heir_id in heirs:
                events.append(("inheritance", heir_id, share))

        # Transfer property
        for asset_id in agent.economy.assets:
            if heirs:
                events.append(("property_transfer", heirs[0], asset_id))

        # Release from employer
        if agent.economy.employer_id:
            events.append(("job_vacancy", agent.economy.employer_id, agent.economy.profession))

        # Social network notification
        for friend_id in agent.social.friends:
            events.append(("death_notification", friend_id, agent.agent_id))

        return events
```

## Population Dynamics Regulators

```python
class PopulationRegulator:
    """Prevents population extinction or explosion."""
    MIN_POPULATION = 20          # Below this, spawn immigrants
    MAX_POPULATION = 10000       # Above this, reduce fertility
    IMMIGRATION_RATE = 0.001     # Per tick when below minimum

    def regulate(self, world: WorldState, tick: int) -> list:
        """Apply population guardrails."""
        population = len([a for a in world.get_all_agents() if a.biology.is_alive])
        events = []

        if population < self.MIN_POPULATION:
            # Spawn immigrants with random skills
            if random.random() < self.IMMIGRATION_RATE * (self.MIN_POPULATION - population):
                events.append(("spawn_immigrant", self._random_immigrant_profile()))

        if population > self.MAX_POPULATION * 0.9:
            # Reduce fertility globally (simulate overcrowding stress)
            events.append(("fertility_modifier", 0.5))

        return events

    def _random_immigrant_profile(self) -> dict:
        return {
            "age_ticks": random.randint(4000, 8000),  # Adult
            "skills": {random.choice(list(PROFESSIONS.keys())): random.uniform(0.2, 0.6)},
            "cash": random.uniform(10, 100),
        }
```
