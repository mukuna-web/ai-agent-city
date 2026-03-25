"""Enhanced skill system with XP curves, skill checks, and specialization tracking."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class SkillInfo:
    name: str
    proficiency: float = 0.1  # 0.0 - 1.0
    xp: int = 0
    times_used: int = 0
    successes: int = 0
    failures: int = 0

    @property
    def level(self) -> int:
        return int(self.proficiency * 20)

    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 0.0
        return self.successes / self.times_used

    @property
    def xp_to_next_level(self) -> int:
        return 100 + self.level * 50

    @property
    def xp_progress(self) -> float:
        threshold = self.xp_to_next_level
        return min(1.0, self.xp / threshold) if threshold > 0 else 1.0


class SkillSystem:
    """Manages all skills for a single agent."""

    SKILL_NAMES = ["foraging", "crafting", "trading", "building", "socializing"]

    # Which actions train which skills
    SKILL_ACTION_MAP = {
        "gather": "foraging",
        "work": "crafting",
        "trade": "trading",
        "build": "building",
        "communicate": "socializing",
        "learn": None,  # learn can train any skill
    }

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self.skills: dict[str, SkillInfo] = {
            name: SkillInfo(name=name) for name in self.SKILL_NAMES
        }

    def practice(self, skill_name: str, difficulty: float = 0.5, xp_amount: int = 10) -> bool:
        """Practice a skill. Returns True if the skill check succeeds."""
        skill = self.skills.get(skill_name)
        if skill is None:
            return False

        skill.times_used += 1
        success = self.check(skill_name, difficulty)

        if success:
            skill.successes += 1
            actual_xp = xp_amount
        else:
            skill.failures += 1
            actual_xp = max(1, xp_amount // 3)  # still learn from failure

        # Harder tasks give bonus XP
        difficulty_bonus = int(difficulty * 5)
        skill.xp += actual_xp + difficulty_bonus

        # Level up check
        if skill.xp >= skill.xp_to_next_level:
            skill.xp -= skill.xp_to_next_level
            skill.proficiency = min(1.0, skill.proficiency + 0.05)

        return success

    def check(self, skill_name: str, difficulty: float = 0.5) -> bool:
        """Skill check: success probability = proficiency adjusted by difficulty."""
        skill = self.skills.get(skill_name)
        if skill is None:
            return False
        # Higher proficiency and lower difficulty = higher success chance
        chance = skill.proficiency / max(0.1, difficulty)
        chance = min(0.95, max(0.05, chance))  # always 5-95% chance
        return self._rng.random() < chance

    def get_proficiency(self, skill_name: str) -> float:
        skill = self.skills.get(skill_name)
        return skill.proficiency if skill else 0.0

    def get_best_skill(self) -> tuple[str, float]:
        best = max(self.skills.values(), key=lambda s: s.proficiency)
        return best.name, best.proficiency

    def get_specialization(self) -> str:
        """Return the agent's primary specialization based on usage patterns."""
        if not any(s.times_used > 0 for s in self.skills.values()):
            return "none"
        return max(self.skills.values(), key=lambda s: s.times_used).name

    def get_summary(self) -> dict:
        return {
            name: {
                "proficiency": round(s.proficiency, 3),
                "level": s.level,
                "xp": s.xp,
                "xp_needed": s.xp_to_next_level,
                "times_used": s.times_used,
                "success_rate": round(s.success_rate, 2),
            }
            for name, s in self.skills.items()
        }

    def total_proficiency(self) -> float:
        return sum(s.proficiency for s in self.skills.values())

    def __repr__(self) -> str:
        parts = [f"{s.name}={s.proficiency:.2f}" for s in self.skills.values()]
        return f"Skills({', '.join(parts)})"
