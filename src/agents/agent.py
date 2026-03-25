"""Main Agent composite — frozen dataclass composing all agent components."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, replace

from .biology import AgentBiology
from .economy import AgentEconomy
from .goals import AgentGoals
from .identity import AgentIdentity
from .needs import AgentNeeds
from .personality import AgentPersonality
from .skills import AgentSkills
from .social import AgentSocial


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


@dataclass(frozen=True, slots=True)
class Agent:
    """Top-level agent entity composing all ECS components.

    All updates return new Agent instances (fully immutable).

    Attributes:
        identity: Identification and lineage data.
        biology: Lifecycle, health, and fertility state.
        needs: Maslow-inspired need hierarchy.
        personality: Big Five personality traits.
        skills: Skill proficiencies, experience, and talent.
        economy: Financial state and employment.
        social: Relationships, kinship, and reputation.
        goals: Goal hierarchy and active plan.
    """

    identity: AgentIdentity
    biology: AgentBiology
    needs: AgentNeeds
    personality: AgentPersonality
    skills: AgentSkills
    economy: AgentEconomy
    social: AgentSocial
    goals: AgentGoals

    # --- Immutable update helpers ---

    def with_needs(self, new_needs: AgentNeeds) -> Agent:
        """Return a new Agent with updated needs."""
        return replace(self, needs=new_needs)

    def with_biology(self, new_bio: AgentBiology) -> Agent:
        """Return a new Agent with updated biology."""
        return replace(self, biology=new_bio)

    def with_skills(self, new_skills: AgentSkills) -> Agent:
        """Return a new Agent with updated skills."""
        return replace(self, skills=new_skills)

    def with_economy(self, new_econ: AgentEconomy) -> Agent:
        """Return a new Agent with updated economy."""
        return replace(self, economy=new_econ)

    def with_goals(self, new_goals: AgentGoals) -> Agent:
        """Return a new Agent with updated goals."""
        return replace(self, goals=new_goals)

    def with_social(self, new_social: AgentSocial) -> Agent:
        """Return a new Agent with updated social state."""
        return replace(self, social=new_social)

    # --- Factory class methods ---

    @classmethod
    def create_founder(
        cls,
        name: str,
        skills: dict[str, float],
        personality: AgentPersonality,
        tick: int = 0,
    ) -> Agent:
        """Create an adult founder agent for the initial population.

        Args:
            name: Display name for the agent.
            skills: Initial skill proficiencies.
            personality: Pre-generated personality.
            tick: Current simulation tick.

        Returns:
            A new adult Agent with reasonable defaults.
        """
        age = random.randint(4000, 10000)
        all_skills = [
            "farming", "mining", "construction", "crafting", "trading",
            "logistics", "teaching", "medicine", "engineering",
            "administration", "manufacturing",
        ]
        talents = {
            s: _clamp(random.gauss(0.5, 0.15), 0.1, 1.0) for s in all_skills
        }

        return cls(
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

    @classmethod
    def create_child(
        cls,
        parent_a: Agent,
        parent_b: Agent,
        tick: int,
    ) -> Agent:
        """Create a child agent with traits inherited from two parents.

        Args:
            parent_a: First parent agent.
            parent_b: Second parent agent.
            tick: Current simulation tick (birth tick).

        Returns:
            A new child Agent with inherited personality and talent.
        """
        personality = AgentPersonality.inherit(
            parent_a.personality, parent_b.personality
        )

        # Inherit skill talents — average of parents plus noise
        all_skills = set(parent_a.skills.talent) | set(parent_b.skills.talent)
        talents: dict[str, float] = {}
        for skill in all_skills:
            parent_avg = (
                parent_a.skills.get_talent(skill)
                + parent_b.skills.get_talent(skill)
            ) / 2.0
            talents[skill] = _clamp(
                parent_avg + random.gauss(0, 0.15), 0.1, 1.0
            )

        generation = (
            max(parent_a.identity.generation, parent_b.identity.generation) + 1
        )
        name = f"Child_{str(uuid.uuid4())[:8]}"

        return cls(
            identity=AgentIdentity(
                agent_id=str(uuid.uuid4()),
                name=name,
                birth_tick=tick,
                parent_ids=(
                    parent_a.identity.agent_id,
                    parent_b.identity.agent_id,
                ),
                generation=generation,
            ),
            biology=AgentBiology(
                age_ticks=0,
                lifecycle_stage="child",
                health=1.0,
                max_health=1.0,
                fertility=0.0,
                is_alive=True,
                cause_of_death=None,
            ),
            needs=AgentNeeds(
                food=1.0,
                water=1.0,
                shelter=1.0,
                rest=1.0,
                health=1.0,
                safety=1.0,
                belonging=1.0,
                esteem=0.5,
                self_actualization=0.1,
            ),
            personality=personality,
            skills=AgentSkills(skills={}, experience={}, talent=talents),
            economy=AgentEconomy(
                cash=0,
                assets=(),
                employer_id=None,
                profession=None,
                wage=0,
                daily_expenses=0,
                savings_target=0,
                debt=0,
                owned_firm_id=None,
            ),
            social=AgentSocial(
                household_id=parent_a.social.household_id,
                partner_id=None,
                children_ids=(),
                parent_ids=(
                    parent_a.identity.agent_id,
                    parent_b.identity.agent_id,
                ),
                friends={},
                trust={},
                reputation=0.5,
                social_class="middle",
            ),
            goals=AgentGoals(
                immediate=[], short_term=[], long_term=[], active_plan=None
            ),
        )
