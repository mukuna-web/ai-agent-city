"""Agent skills component — skill progression with diminishing returns and teaching."""

from __future__ import annotations

from dataclasses import dataclass, replace


# Skill system constants
SKILL_DECAY_RATE: float = 0.0001
SKILL_GAIN_BASE: float = 0.0005
MAX_SKILL: float = 1.0
TEACHING_MULTIPLIER_MIN: float = 3.0
TEACHING_MULTIPLIER_MAX: float = 5.0
PASSIVE_ABSORPTION_RATE: float = 0.0001


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


@dataclass(frozen=True, slots=True)
class AgentSkills:
    """Immutable skill state for an agent.

    Attributes:
        skills: Mapping of skill name to proficiency level (0.0 to 1.0).
        experience: Mapping of skill name to total ticks practiced.
        talent: Innate aptitude multiplier per skill, set at birth (0.0 to 1.0).
    """

    skills: dict[str, float]
    experience: dict[str, int]
    talent: dict[str, float]

    def get_skill(self, skill_name: str) -> float:
        """Get current proficiency for a skill, defaulting to 0.0."""
        return self.skills.get(skill_name, 0.0)

    def get_talent(self, skill_name: str) -> float:
        """Get innate talent for a skill, defaulting to 0.5."""
        return self.talent.get(skill_name, 0.5)

    def get_experience(self, skill_name: str) -> int:
        """Get total experience ticks for a skill, defaulting to 0."""
        return self.experience.get(skill_name, 0)


class SkillSystem:
    """Stateless system for skill progression, decay, teaching, and inheritance.

    All methods return new AgentSkills instances (immutable updates).
    """

    def practice(
        self,
        agent_skills: AgentSkills,
        skill_name: str,
        intensity: float = 1.0,
    ) -> AgentSkills:
        """Improve a skill through practice with diminishing returns.

        Gain formula: base * talent * intensity * (1 - current_skill)
        The (1 - current_skill) factor provides diminishing returns at
        higher proficiency levels.

        Args:
            agent_skills: Current skill state.
            skill_name: The skill to practice.
            intensity: Practice intensity multiplier (default 1.0).

        Returns:
            New AgentSkills with improved proficiency and updated experience.
        """
        current = agent_skills.get_skill(skill_name)
        talent = agent_skills.get_talent(skill_name)
        exp = agent_skills.get_experience(skill_name)

        # Diminishing returns: harder to improve as you get better
        diminishing = 1.0 - current
        gain = SKILL_GAIN_BASE * talent * intensity * diminishing
        new_level = _clamp(current + gain, 0.0, MAX_SKILL)

        new_skills = {**agent_skills.skills, skill_name: new_level}
        new_experience = {**agent_skills.experience, skill_name: exp + 1}

        return replace(
            agent_skills,
            skills=new_skills,
            experience=new_experience,
        )

    def decay_unused(
        self,
        agent_skills: AgentSkills,
        active_skill: str | None = None,
    ) -> AgentSkills:
        """Decay all skills except the currently active one.

        Inactive skills lose proficiency at SKILL_DECAY_RATE per tick.

        Args:
            agent_skills: Current skill state.
            active_skill: Skill currently in use (exempt from decay).

        Returns:
            New AgentSkills with decayed inactive skills.
        """
        new_skills: dict[str, float] = {}
        for name, level in agent_skills.skills.items():
            if name == active_skill:
                new_skills[name] = level
            else:
                decayed = max(0.0, level - SKILL_DECAY_RATE)
                new_skills[name] = decayed

        return replace(agent_skills, skills=new_skills)

    def teach(
        self,
        teacher_skills: AgentSkills,
        student_skills: AgentSkills,
        skill_name: str,
    ) -> AgentSkills:
        """Transfer knowledge from teacher to student (3-5x faster learning).

        The teaching multiplier scales with teacher proficiency.
        The student must be below the teacher's level to benefit.

        Args:
            teacher_skills: The teacher's skill state.
            student_skills: The student's skill state.
            skill_name: The skill being taught.

        Returns:
            New AgentSkills for the student with improved proficiency.
        """
        teacher_level = teacher_skills.get_skill(skill_name)
        student_level = student_skills.get_skill(skill_name)

        # Student can only learn up to the teacher's level
        if student_level >= teacher_level:
            return student_skills

        # Teaching multiplier scales with teacher skill
        teaching_mult = (
            TEACHING_MULTIPLIER_MIN
            + (TEACHING_MULTIPLIER_MAX - TEACHING_MULTIPLIER_MIN) * teacher_level
        )

        talent = student_skills.get_talent(skill_name)
        diminishing = 1.0 - student_level
        gain = SKILL_GAIN_BASE * talent * teaching_mult * diminishing
        new_level = _clamp(student_level + gain, 0.0, min(teacher_level, MAX_SKILL))

        new_skills = {**student_skills.skills, skill_name: new_level}
        new_exp = {
            **student_skills.experience,
            skill_name: student_skills.get_experience(skill_name) + 1,
        }

        return replace(student_skills, skills=new_skills, experience=new_exp)

    def inherit_from_parent(
        self,
        child_skills: AgentSkills,
        parent_skills: AgentSkills,
    ) -> AgentSkills:
        """Passive skill absorption from a parent in the same household.

        Children absorb a tiny fraction of parent skills each tick,
        representing environmental exposure (watching a parent work).

        Args:
            child_skills: The child's current skill state.
            parent_skills: The parent's skill state.

        Returns:
            New AgentSkills for the child with slightly improved skills.
        """
        new_skills = dict(child_skills.skills)
        for name, parent_level in parent_skills.skills.items():
            child_level = new_skills.get(name, 0.0)
            talent = child_skills.get_talent(name)
            absorption = PASSIVE_ABSORPTION_RATE * parent_level * talent
            new_skills[name] = _clamp(child_level + absorption, 0.0, MAX_SKILL)

        return replace(child_skills, skills=new_skills)
