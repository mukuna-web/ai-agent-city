# Profession System — Causal Consequences

## Design Principle

Every profession performs REAL work that has CAUSAL effects on the city. A farmer
who doesn't farm means less food → higher food prices → hunger → health decline →
hospital demand → doctor shortage. This causal chain is what makes the simulation
non-trivial.

## Profession Registry

```python
PROFESSIONS = {
    "farmer": {
        "category": "primary",
        "building_type": "farm",
        "primary_skill": "farming",
        "secondary_skills": ["logistics"],
        "output_resources": ["wheat", "vegetables", "livestock", "cotton"],
        "input_resources": ["tools", "water_supply"],
        "training_ticks": 500,
        "min_skill": 0.1,
        "base_wage_multiplier": 0.8,  # Relative to average wage
        "essential": True,  # City cannot function without this
        "causal_effects": {
            "produces": "food supply for city",
            "absence_causes": "food scarcity → price spike → hunger → health decline",
        },
    },
    "miner": {
        "category": "primary",
        "building_type": None,  # Works on resource tiles directly
        "primary_skill": "mining",
        "secondary_skills": ["strength"],
        "output_resources": ["iron_ore", "stone", "coal", "clay"],
        "input_resources": ["tools"],
        "training_ticks": 400,
        "min_skill": 0.1,
        "base_wage_multiplier": 0.9,
        "essential": True,
        "causal_effects": {
            "produces": "raw materials for construction and manufacturing",
            "absence_causes": "material shortage → construction stops → no new buildings",
        },
    },
    "builder": {
        "category": "secondary",
        "building_type": None,  # Works at construction sites
        "primary_skill": "construction",
        "secondary_skills": ["strength", "crafting"],
        "output_resources": [],  # Produces buildings, not resources
        "input_resources": ["lumber", "bricks", "iron", "tools"],
        "training_ticks": 600,
        "min_skill": 0.2,
        "base_wage_multiplier": 1.0,
        "essential": True,
        "causal_effects": {
            "produces": "new buildings — houses, workshops, infrastructure",
            "absence_causes": "no new buildings → housing shortage → homelessness → population cap",
        },
    },
    "craftsman": {
        "category": "secondary",
        "building_type": "workshop",
        "primary_skill": "crafting",
        "secondary_skills": ["trading"],
        "output_resources": ["tools", "clothing", "bread", "meat"],
        "input_resources": ["iron", "timber", "wheat", "cotton", "livestock"],
        "training_ticks": 800,
        "min_skill": 0.2,
        "base_wage_multiplier": 1.1,
        "essential": True,
        "causal_effects": {
            "produces": "processed goods — tools, clothing, food products",
            "absence_causes": "no tools → all production slows. no bread → food crisis",
        },
    },
    "trader": {
        "category": "tertiary",
        "building_type": "market",
        "primary_skill": "trading",
        "secondary_skills": ["logistics"],
        "output_resources": [],  # Moves goods, doesn't produce
        "input_resources": [],
        "training_ticks": 400,
        "min_skill": 0.15,
        "base_wage_multiplier": 1.2,
        "essential": False,
        "causal_effects": {
            "produces": "market liquidity — connects buyers and sellers",
            "absence_causes": "markets dry up → price discovery fails → inefficient economy",
        },
    },
    "logistics_worker": {
        "category": "tertiary",
        "building_type": "warehouse",
        "primary_skill": "logistics",
        "secondary_skills": ["strength"],
        "output_resources": [],
        "input_resources": [],
        "training_ticks": 300,
        "min_skill": 0.1,
        "base_wage_multiplier": 0.85,
        "essential": True,
        "causal_effects": {
            "produces": "goods transport between buildings/districts",
            "absence_causes": "production piles up at source, shortages at destination",
        },
    },
    "teacher": {
        "category": "service",
        "building_type": "school",
        "primary_skill": "teaching",
        "secondary_skills": [],
        "output_resources": [],
        "input_resources": [],
        "training_ticks": 1000,
        "min_skill": 0.4,
        "base_wage_multiplier": 1.0,
        "essential": False,
        "causal_effects": {
            "produces": "skill training for children and adults",
            "absence_causes": "children grow up unskilled → low productivity → poverty trap",
        },
    },
    "doctor": {
        "category": "service",
        "building_type": "hospital",
        "primary_skill": "medicine",
        "secondary_skills": [],
        "output_resources": ["medicine"],
        "input_resources": [],
        "training_ticks": 2000,
        "min_skill": 0.5,
        "base_wage_multiplier": 2.0,
        "essential": True,
        "causal_effects": {
            "produces": "health restoration, disease treatment",
            "absence_causes": "untreated illness → death rate spikes → population decline",
        },
    },
    "engineer": {
        "category": "service",
        "building_type": "power_plant",
        "primary_skill": "engineering",
        "secondary_skills": ["crafting"],
        "output_resources": ["electricity"],
        "input_resources": ["coal", "tools"],
        "training_ticks": 1500,
        "min_skill": 0.4,
        "base_wage_multiplier": 1.8,
        "essential": True,
        "causal_effects": {
            "produces": "power generation, infrastructure maintenance",
            "absence_causes": "power grid fails → factories stop → workshops stop → economic collapse",
        },
    },
    "bureaucrat": {
        "category": "governance",
        "building_type": "town_hall",
        "primary_skill": "administration",
        "secondary_skills": ["trading"],
        "output_resources": [],
        "input_resources": [],
        "training_ticks": 800,
        "min_skill": 0.3,
        "base_wage_multiplier": 1.3,
        "essential": False,
        "causal_effects": {
            "produces": "tax collection, law enforcement, public service administration",
            "absence_causes": "no tax collection → no public services → infrastructure decay",
        },
    },
    "factory_worker": {
        "category": "secondary",
        "building_type": "factory",
        "primary_skill": "manufacturing",
        "secondary_skills": ["strength"],
        "output_resources": [],  # Determined by factory's recipes
        "input_resources": [],
        "training_ticks": 400,
        "min_skill": 0.15,
        "base_wage_multiplier": 0.95,
        "essential": False,
        "causal_effects": {
            "produces": "mass-produced goods at 3x workshop rate",
            "absence_causes": "production bottleneck at scale, economy stays artisanal",
        },
    },
    "entrepreneur": {
        "category": "leadership",
        "building_type": None,
        "primary_skill": "trading",
        "secondary_skills": ["administration"],
        "output_resources": [],
        "input_resources": [],
        "training_ticks": 0,  # No formal training — self-selected
        "min_skill": 0.3,
        "base_wage_multiplier": 0,  # Earns from firm profits, not wages
        "essential": False,
        "causal_effects": {
            "produces": "new firms, new jobs, economic dynamism",
            "absence_causes": "no new businesses → stagnant economy → no innovation",
        },
    },
}
```

## Profession Assignment — How Agents Choose Careers

```python
class ProfessionAssignment:
    def evaluate_profession(self, agent: Agent, profession: str,
                            world: WorldState) -> float:
        """Score how attractive a profession is for this agent."""
        spec = PROFESSIONS[profession]

        # Skill match — does agent have talent/training?
        primary_skill = agent.skills.skills.get(spec["primary_skill"], 0)
        talent = agent.skills.talent.get(spec["primary_skill"], 0.5)
        skill_score = primary_skill * 0.4 + talent * 0.6

        # Wage attractiveness
        market_wage = world.labor_market.calculate_market_wage(profession)
        current_wage = agent.economy.wage
        wage_score = market_wage / max(current_wage, 0.1) if current_wage > 0 else market_wage

        # Job availability
        openings = len([p for p in world.labor_market.postings
                       if p.profession == profession and not p.filled])
        availability_score = min(openings / 3, 1.0)

        # Personality fit
        personality_fit = self._personality_match(agent.personality, profession)

        # Social influence — do friends/family do this?
        social_score = self._social_influence(agent, profession, world)

        return (
            skill_score * 0.30 +
            wage_score * 0.25 +
            availability_score * 0.20 +
            personality_fit * 0.15 +
            social_score * 0.10
        )

    def choose_profession(self, agent: Agent, world: WorldState) -> str | None:
        """Agent picks highest-scoring available profession."""
        scores = {}
        for profession in PROFESSIONS:
            spec = PROFESSIONS[profession]
            if agent.skills.skills.get(spec["primary_skill"], 0) >= spec["min_skill"]:
                scores[profession] = self.evaluate_profession(agent, profession, world)
            elif agent.skills.talent.get(spec["primary_skill"], 0.5) > 0.6:
                # High talent but untrained — willing to train
                scores[profession] = self.evaluate_profession(agent, profession, world) * 0.5

        if not scores:
            return None  # No suitable profession found

        return max(scores, key=scores.get)

    def _personality_match(self, personality, profession: str) -> float:
        """Some personalities suit certain professions better."""
        matches = {
            "farmer": personality.conscientiousness * 0.5 + (1 - personality.neuroticism) * 0.5,
            "trader": personality.extraversion * 0.4 + personality.openness * 0.3 + (1 - personality.agreeableness) * 0.3,
            "teacher": personality.agreeableness * 0.4 + personality.conscientiousness * 0.3 + personality.extraversion * 0.3,
            "doctor": personality.conscientiousness * 0.4 + personality.agreeableness * 0.3 + (1 - personality.neuroticism) * 0.3,
            "entrepreneur": personality.openness * 0.3 + (1 - personality.agreeableness) * 0.3 + personality.extraversion * 0.2 + (1 - personality.neuroticism) * 0.2,
            "builder": personality.conscientiousness * 0.5 + (1 - personality.openness) * 0.3 + (1 - personality.neuroticism) * 0.2,
            "engineer": personality.conscientiousness * 0.4 + personality.openness * 0.3 + (1 - personality.extraversion) * 0.3,
        }
        return matches.get(profession, 0.5)

    def _social_influence(self, agent, profession, world) -> float:
        """Friends/family in this profession increase attractiveness."""
        count = 0
        for friend_id in agent.social.friends:
            friend = world.get_agent(friend_id)
            if friend and friend.economy.profession == profession:
                count += 1
        for parent_id in agent.social.parent_ids:
            parent = world.get_agent(parent_id)
            if parent and parent.economy.profession == profession:
                count += 2  # Parents have stronger influence
        return min(count / 5, 1.0)
```

## Skill Training and Improvement

```python
class SkillSystem:
    SKILL_DECAY_RATE = 0.0001   # Per tick when not practicing
    SKILL_GAIN_BASE = 0.0005    # Per tick when practicing
    MAX_SKILL = 1.0

    def practice(self, agent: Agent, skill: str, intensity: float = 1.0) -> Agent:
        """Improve a skill through practice. Diminishing returns at higher levels."""
        current = agent.skills.skills.get(skill, 0)
        talent = agent.skills.talent.get(skill, 0.5)

        # Gain rate = base * talent * (1 - current_level)^2 * intensity
        # Diminishing returns: harder to improve as you get better
        gain = self.SKILL_GAIN_BASE * talent * ((1 - current) ** 2) * intensity
        new_level = min(current + gain, self.MAX_SKILL)

        new_skills = {**agent.skills.skills, skill: new_level}
        new_experience = {**agent.skills.experience, skill: agent.skills.experience.get(skill, 0) + 1}

        return agent._replace(skills=agent.skills._replace(
            skills=new_skills, experience=new_experience
        ))

    def decay_unused(self, agent: Agent, active_skill: str | None) -> Agent:
        """Skills not being used slowly decay."""
        new_skills = {}
        for skill, level in agent.skills.skills.items():
            if skill == active_skill:
                new_skills[skill] = level
            else:
                new_skills[skill] = max(0, level - self.SKILL_DECAY_RATE)
        return agent._replace(skills=agent.skills._replace(skills=new_skills))

    def teach(self, teacher: Agent, student: Agent, skill: str) -> Agent:
        """Teacher transfers skill knowledge. Faster than self-practice."""
        teacher_level = teacher.skills.skills.get(skill, 0)
        teaching_skill = teacher.skills.skills.get("teaching", 0.1)
        student_talent = student.skills.talent.get(skill, 0.5)

        # Teaching is 3-5x faster than self-practice
        gain = self.SKILL_GAIN_BASE * 4 * teaching_skill * student_talent * teacher_level
        current = student.skills.skills.get(skill, 0)
        new_level = min(current + gain, teacher_level * 0.9)  # Can't exceed teacher

        new_skills = {**student.skills.skills, skill: new_level}
        return student._replace(skills=student.skills._replace(skills=new_skills))

    def inherit_from_parent(self, child: Agent, parent: Agent) -> Agent:
        """Children passively absorb skills from parents during childhood."""
        new_skills = dict(child.skills.skills)
        for skill, level in parent.skills.skills.items():
            current = new_skills.get(skill, 0)
            # Passive absorption: very slow, capped at 20% of parent level
            gain = level * 0.0001  # Per tick
            new_skills[skill] = min(current + gain, level * 0.2)
        return child._replace(skills=child.skills._replace(skills=new_skills))
```

## Labor Shortage Resolution

```python
class LaborShortageResolver:
    """Detects and responds to critical labor shortages."""

    def detect_shortages(self, world: WorldState) -> list[dict]:
        shortages = []
        for profession, spec in PROFESSIONS.items():
            if not spec["essential"]:
                continue

            # Count workers in this profession
            workers = [a for a in world.get_all_agents()
                      if a.economy.profession == profession
                      and a.biology.lifecycle_stage in ("adult", "elder")]

            # Estimate demand
            demand = self._estimate_demand(profession, world)

            if len(workers) < demand * 0.5:  # Less than 50% of needed
                shortages.append({
                    "profession": profession,
                    "current_workers": len(workers),
                    "estimated_demand": demand,
                    "severity": 1 - (len(workers) / max(demand, 1)),
                })

        return sorted(shortages, key=lambda s: -s["severity"])

    def resolve(self, shortages: list[dict], world: WorldState) -> list[str]:
        """Take action to resolve shortages."""
        actions = []
        for shortage in shortages:
            prof = shortage["profession"]

            # 1. Raise wages to attract workers
            current_wage = world.labor_market.calculate_market_wage(prof)
            new_wage = current_wage * (1 + shortage["severity"] * 0.5)
            actions.append(f"Raised {prof} wage to {new_wage:.2f}")

            # 2. If severity > 0.8 and essential, spawn NPC filler
            if shortage["severity"] > 0.8 and PROFESSIONS[prof]["essential"]:
                actions.append(f"CRITICAL: Spawning emergency NPC {prof}")
                # This is the safety valve — prevents simulation collapse

        return actions

    def _estimate_demand(self, profession: str, world: WorldState) -> int:
        """How many workers does the city need for this profession?"""
        population = len(world.get_all_agents())
        ratios = {
            "farmer": 0.15,        # 15% of pop should be farmers
            "miner": 0.05,
            "builder": 0.08,
            "craftsman": 0.08,
            "doctor": 0.03,
            "engineer": 0.03,
            "logistics_worker": 0.05,
            "teacher": 0.04,
            "bureaucrat": 0.02,
        }
        return max(1, int(population * ratios.get(profession, 0.05)))
```

## Profession Evolution with Civilization Advancement

```
ERA 1: SETTLEMENT (0 - 10,000 ticks)
  Available: farmer, miner, builder, craftsman
  City size: 50-100 agents
  Focus: survival, basic shelter, food production

ERA 2: TOWN (10,000 - 50,000 ticks)
  Unlocked: trader, teacher, doctor, logistics_worker
  Requires: market building, school, hospital exist
  City size: 100-500 agents

ERA 3: CITY (50,000 - 200,000 ticks)
  Unlocked: engineer, bureaucrat, factory_worker, entrepreneur
  Requires: power plant, town hall, factory exist
  City size: 500-2000 agents

ERA 4: METROPOLIS (200,000+ ticks)
  Unlocked: researcher, politician, banker, lawyer
  Requires: university, bank, courthouse exist
  City size: 2000+ agents
```
