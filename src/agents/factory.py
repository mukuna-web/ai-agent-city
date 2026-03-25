"""Agent factory for creating the initial founding population."""

from __future__ import annotations

import random
import uuid

from .agent import Agent
from .biology import AgentBiology
from .economy import AgentEconomy
from .goals import AgentGoals
from .identity import AgentIdentity
from .needs import AgentNeeds
from .personality import AgentPersonality
from .skills import AgentSkills
from .social import AgentSocial

NAMES: tuple[str, ...] = (
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Kate", "Leo", "Maya", "Noah", "Olive", "Paul",
    "Quinn", "Rose", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zane",
)

ALL_SKILLS: tuple[str, ...] = (
    "farming", "mining", "construction", "crafting", "trading",
    "logistics", "teaching", "medicine", "engineering",
    "administration", "manufacturing",
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def create_founder_population(count: int, tick: int = 0) -> list[Agent]:
    """Create the founding population of the city.

    Generates adults with random personalities, talents, and 1-2
    starting skills partially trained.

    Args:
        count: Number of agents to create.
        tick: Current simulation tick (used to backdate birth ticks).

    Returns:
        A list of newly created adult Agent instances.
    """
    agents: list[Agent] = []

    for i in range(count):
        name = random.choice(NAMES) + f"_{i}"
        personality = AgentPersonality.random()

        # Random skill talents
        talents = {
            skill: _clamp(random.gauss(0.5, 0.15), 0.1, 1.0)
            for skill in ALL_SKILLS
        }

        # Start with 1-2 skills partially trained
        starting_skills = random.sample(list(ALL_SKILLS), k=random.randint(1, 2))
        skills = {s: random.uniform(0.2, 0.5) for s in starting_skills}

        age = random.randint(4000, 10000)

        agent = Agent(
            identity=AgentIdentity(
                agent_id=str(uuid.uuid4()),
                name=name,
                birth_tick=tick - age,
                parent_ids=None,
                generation=0,
            ),
            biology=AgentBiology(
                age_ticks=age,
                lifecycle_stage="adult",
                health=random.uniform(0.8, 1.0),
                max_health=1.0,
                fertility=random.uniform(0.5, 0.9),
                is_alive=True,
                cause_of_death=None,
            ),
            needs=AgentNeeds(
                food=random.uniform(0.6, 1.0),
                water=random.uniform(0.6, 1.0),
                shelter=0.3,
                rest=random.uniform(0.5, 1.0),
                health=1.0,
                safety=0.8,
                belonging=0.3,
                esteem=0.3,
                self_actualization=0.1,
            ),
            personality=personality,
            skills=AgentSkills(skills=skills, experience={}, talent=talents),
            economy=AgentEconomy(
                cash=random.uniform(50, 200),
                assets=(),
                employer_id=None,
                profession=None,
                wage=0,
                daily_expenses=0,
                savings_target=500,
                debt=0,
                owned_firm_id=None,
            ),
            social=AgentSocial(
                household_id=None,
                partner_id=None,
                children_ids=(),
                parent_ids=(),
                friends={},
                trust={},
                reputation=0.5,
                social_class="middle",
            ),
            goals=AgentGoals(
                immediate=[], short_term=[], long_term=[], active_plan=None
            ),
        )
        agents.append(agent)

    return agents
