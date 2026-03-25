"""Reward shaping for more nuanced agent learning.

Provides potential-based reward shaping that guides agents toward
beneficial behaviors without changing the optimal policy. Rewards
are shaped by agent state, environmental context, and social factors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent import Agent, Action, ActionType


class RewardShaper:
    """Computes shaped rewards based on agent state transitions.

    Uses potential-based shaping: F(s,s') = gamma * phi(s') - phi(s)
    This guarantees the optimal policy is preserved while accelerating learning.
    """

    def __init__(self, gamma: float = 0.95, weights: dict[str, float] | None = None):
        self.gamma = gamma
        self.weights = weights or {
            "energy": 1.0,
            "wealth": 0.8,
            "skills": 1.2,
            "social": 0.6,
            "mood": 0.4,
            "survival": 2.0,
        }

    def potential(self, agent: Agent) -> float:
        """Compute state potential — higher is better."""
        p = 0.0

        # Energy potential: being healthy is good
        energy_ratio = agent.energy / agent.max_energy
        p += self.weights["energy"] * energy_ratio

        # Wealth potential: having coins and inventory
        coin_potential = min(1.0, agent.coins / 200.0)
        inv_potential = min(1.0, agent.inventory.total / agent.inventory.capacity)
        p += self.weights["wealth"] * (coin_potential * 0.6 + inv_potential * 0.4)

        # Skill potential: average skill level
        if agent.skills:
            avg_skill = sum(agent.skills.values()) / len(agent.skills)
            p += self.weights["skills"] * avg_skill

        # Social potential: trust network size and strength
        if agent.trust:
            avg_trust = sum(agent.trust.values()) / len(agent.trust)
            network_size = min(1.0, len(agent.trust) / 10.0)
            p += self.weights["social"] * (avg_trust * 0.5 + network_size * 0.5)

        # Mood potential
        p += self.weights["mood"] * agent.mood

        # Survival penalty: harsh penalty near death
        if agent.energy < 15:
            p -= self.weights["survival"] * (1.0 - energy_ratio)

        return p

    def shape(self, agent_before: dict, agent_after: Agent, base_reward: float) -> float:
        """Compute shaped reward: base_reward + gamma * phi(s') - phi(s).

        agent_before should be a snapshot dict with keys: energy, max_energy,
        coins, inventory_total, inventory_capacity, skills, trust, mood.
        """
        phi_before = self._potential_from_snapshot(agent_before)
        phi_after = self.potential(agent_after)

        shaping_bonus = self.gamma * phi_after - phi_before
        return base_reward + shaping_bonus

    def _potential_from_snapshot(self, snap: dict) -> float:
        p = 0.0
        max_energy = snap.get("max_energy", 100.0)
        energy = snap.get("energy", 50.0)
        energy_ratio = energy / max_energy if max_energy > 0 else 0.0
        p += self.weights["energy"] * energy_ratio

        coins = snap.get("coins", 0)
        inv_total = snap.get("inventory_total", 0)
        inv_cap = snap.get("inventory_capacity", 20)
        coin_potential = min(1.0, coins / 200.0)
        inv_potential = min(1.0, inv_total / inv_cap) if inv_cap > 0 else 0.0
        p += self.weights["wealth"] * (coin_potential * 0.6 + inv_potential * 0.4)

        skills = snap.get("skills", {})
        if skills:
            avg_skill = sum(skills.values()) / len(skills)
            p += self.weights["skills"] * avg_skill

        trust = snap.get("trust", {})
        if trust:
            avg_trust = sum(trust.values()) / len(trust)
            network_size = min(1.0, len(trust) / 10.0)
            p += self.weights["social"] * (avg_trust * 0.5 + network_size * 0.5)

        mood = snap.get("mood", 0.5)
        p += self.weights["mood"] * mood

        if energy < 15:
            p -= self.weights["survival"] * (1.0 - energy_ratio)

        return p

    def compute_context_bonus(self, agent: Agent, action_type: str) -> float:
        """Extra reward based on situational context."""
        bonus = 0.0

        # Reward resting when energy is critically low
        if action_type == "rest" and agent.energy < 25:
            bonus += 1.5

        # Reward gathering when inventory is low
        if action_type == "gather" and agent.inventory.total < 3:
            bonus += 1.0

        # Reward socializing for highly social agents
        if action_type == "communicate" and agent.personality.sociability > 0.7:
            bonus += 0.5

        # Reward learning for curious agents
        if action_type == "learn" and agent.personality.curiosity > 0.7:
            bonus += 0.5

        # Reward working for industrious agents
        if action_type == "work" and agent.personality.industriousness > 0.7:
            bonus += 0.3

        # Penalize overworking when tired
        if action_type == "work" and agent.energy < 20:
            bonus -= 1.0

        return bonus


def snapshot_agent(agent: Agent) -> dict:
    """Capture agent state before action for reward shaping comparison."""
    return {
        "energy": agent.energy,
        "max_energy": agent.max_energy,
        "coins": agent.coins,
        "inventory_total": agent.inventory.total,
        "inventory_capacity": agent.inventory.capacity,
        "skills": dict(agent.skills),
        "trust": dict(agent.trust),
        "mood": agent.mood,
    }
