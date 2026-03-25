"""Learning system — integrates Q-learning, replay, and reward shaping into the ECS simulation.

Runs every 10 ticks (deliberation frequency). Maintains per-agent learners
that persist across ticks while respecting the immutable Agent architecture.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


@dataclass
class Transition:
    state: tuple
    action: str
    reward: float
    next_state: tuple
    tick: int


class PrioritizedReplayBuffer:
    """Replay buffer that samples high-reward transitions more often."""

    def __init__(self, capacity: int = 500, alpha: float = 0.6, seed: int = 42):
        self.capacity = capacity
        self.alpha = alpha
        self.buffer: deque[Transition] = deque(maxlen=capacity)
        self.priorities: deque[float] = deque(maxlen=capacity)
        self._rng = random.Random(seed)

    def push(self, state: tuple, action: str, reward: float, next_state: tuple, tick: int):
        priority = (abs(reward) + 0.01) ** self.alpha
        self.buffer.append(Transition(state=state, action=action, reward=reward,
                                       next_state=next_state, tick=tick))
        self.priorities.append(priority)

    def sample(self, batch_size: int) -> list[Transition]:
        batch_size = min(batch_size, len(self.buffer))
        if batch_size == 0:
            return []
        buf_list = list(self.buffer)
        pri_list = list(self.priorities)
        total = sum(pri_list)
        if total == 0:
            return self._rng.sample(buf_list, batch_size)
        weights = [p / total for p in pri_list]
        chosen = self._rng.choices(buf_list, weights=weights, k=batch_size)
        return chosen

    def __len__(self) -> int:
        return len(self.buffer)


class AgentLearnerState:
    """Per-agent learning state — lives outside the immutable Agent."""

    def __init__(self, agent_id: str, seed: int = 42):
        self.agent_id = agent_id
        self.q_table: dict[tuple, dict[str, float]] = {}
        self.learning_rate: float = 0.1
        self.discount_factor: float = 0.95
        self.epsilon: float = 0.3
        self.epsilon_decay: float = 0.995
        self.epsilon_min: float = 0.01
        self.lr_decay: float = 0.9999
        self.lr_min: float = 0.001
        self.replay = PrioritizedReplayBuffer(capacity=500, seed=seed)
        self._rng = random.Random(seed)
        self.total_updates: int = 0
        self.last_state: tuple | None = None
        self.last_action: str | None = None

    def update_q(self, state: tuple, action: str, reward: float, next_state: tuple) -> float:
        current_q = self.q_table.setdefault(state, {}).get(action, 0.0)
        next_max = max(self.q_table.get(next_state, {}).values(), default=0.0)
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max - current_q
        )
        self.q_table[state][action] = new_q
        return new_q

    def replay_batch(self, batch_size: int = 16):
        if len(self.replay) < batch_size:
            return
        for t in self.replay.sample(batch_size):
            self.update_q(t.state, t.action, t.reward, t.next_state)

    def decay(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.learning_rate = max(self.lr_min, self.learning_rate * self.lr_decay)
        self.total_updates += 1


def discretize_agent_state(agent) -> tuple:
    """Convert immutable Agent into a discrete state tuple for Q-table lookup."""
    needs = agent.needs
    food_level = "low" if needs.food < 0.3 else "mid" if needs.food < 0.7 else "high"
    rest_level = "low" if needs.rest < 0.3 else "mid" if needs.rest < 0.7 else "high"
    health_level = "low" if agent.biology.health < 0.3 else "mid" if agent.biology.health < 0.7 else "high"
    wealth_level = "poor" if agent.economy.cash < 50 else "mid" if agent.economy.cash < 200 else "rich"
    employed = agent.economy.employer_id is not None
    has_partner = agent.social.partner_id is not None
    lifecycle = agent.biology.lifecycle_stage
    return (food_level, rest_level, health_level, wealth_level, employed, has_partner, lifecycle)


def compute_reward(agent, prev_snapshot: dict) -> float:
    """Compute reward based on state changes."""
    reward = 0.0

    # Health improvement/decline
    health_delta = agent.biology.health - prev_snapshot["health"]
    reward += health_delta * 3.0

    # Need satisfaction
    curr_avg_need = (agent.needs.food + agent.needs.water + agent.needs.rest +
                     agent.needs.safety + agent.needs.health) / 5.0
    prev_avg_need = prev_snapshot["avg_need"]
    reward += (curr_avg_need - prev_avg_need) * 2.0

    # Wealth change
    cash_delta = agent.economy.cash - prev_snapshot["cash"]
    reward += min(1.0, cash_delta / 50.0) if cash_delta > 0 else max(-1.0, cash_delta / 50.0)

    # Social reward
    curr_friends = len(agent.social.friends)
    if curr_friends > prev_snapshot["friend_count"]:
        reward += 0.5

    # Survival bonus
    if agent.biology.is_alive:
        reward += 0.1

    # Death penalty
    if not agent.biology.is_alive:
        reward -= 5.0

    return reward


def snapshot_agent_state(agent) -> dict:
    """Capture agent state for reward computation."""
    return {
        "health": agent.biology.health,
        "cash": agent.economy.cash,
        "avg_need": (agent.needs.food + agent.needs.water + agent.needs.rest +
                     agent.needs.safety + agent.needs.health) / 5.0,
        "friend_count": len(agent.social.friends),
    }


class LearningSystem:
    """ECS-compatible learning system.

    Registers as a system with frequency=10 (runs every 10 ticks).
    Maintains learner state per agent, computes rewards from state deltas,
    and updates Q-tables with experience replay.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self.learners: dict[str, AgentLearnerState] = {}
        self._snapshots: dict[str, dict] = {}

    def _ensure_learner(self, agent_id: str) -> AgentLearnerState:
        if agent_id not in self.learners:
            self.learners[agent_id] = AgentLearnerState(
                agent_id, seed=self._rng.randint(0, 999999)
            )
        return self.learners[agent_id]

    def capture_snapshots(self, world: "WorldState"):
        """Call BEFORE actions are resolved each tick to capture pre-action state."""
        for agent_id, agent in world.agents.items():
            if agent.biology.is_alive:
                self._snapshots[agent_id] = snapshot_agent_state(agent)

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        """Main update — compute rewards, update Q-tables, replay."""
        from ..engine.event_bus import Event

        for agent_id, agent in world.agents.items():
            if not agent.biology.is_alive:
                # Clean up dead agents' learners
                if agent_id in self._snapshots:
                    del self._snapshots[agent_id]
                continue

            learner = self._ensure_learner(agent_id)
            current_state = discretize_agent_state(agent)

            # Compute reward from state change
            prev_snap = self._snapshots.get(agent_id)
            if prev_snap and learner.last_state is not None and learner.last_action is not None:
                reward = compute_reward(agent, prev_snap)

                # Q-learning update
                learner.update_q(learner.last_state, learner.last_action, reward, current_state)

                # Store in replay buffer
                learner.replay.push(
                    learner.last_state, learner.last_action,
                    reward, current_state, tick,
                )

                # Periodic replay
                if learner.total_updates % 5 == 0:
                    learner.replay_batch(16)

                learner.decay()

            # Record current state for next update
            learner.last_state = current_state

            # Choose next action via epsilon-greedy (influences cognition)
            actions = ["find_food", "find_water", "go_to_work", "rest",
                       "socialize", "learn_skill", "trade", "wander"]
            if self._rng.random() < learner.epsilon:
                chosen = self._rng.choice(actions)
            else:
                q_vals = learner.q_table.get(current_state, {})
                chosen = max(actions, key=lambda a: q_vals.get(a, 0.0))

            learner.last_action = chosen

            # Update agent's immediate goal based on learning
            # (the cognition system will pick this up)
            if agent.goals.immediate != [chosen]:
                new_goals = agent.goals._replace(immediate=[chosen]) if hasattr(agent.goals, '_replace') else agent.goals
                try:
                    world.agents[agent_id] = agent.with_goals(new_goals)
                except Exception:
                    pass  # Goals might not support direct update in all cases

        # Capture fresh snapshots for next cycle
        self.capture_snapshots(world)

        # Emit learning stats event periodically
        if tick % 100 == 0:
            avg_epsilon = 0.0
            avg_q_size = 0.0
            count = len(self.learners)
            if count > 0:
                avg_epsilon = sum(l.epsilon for l in self.learners.values()) / count
                avg_q_size = sum(len(l.q_table) for l in self.learners.values()) / count

            event_bus.emit(Event(
                tick=tick,
                event_type="learning.stats",
                data={
                    "avg_epsilon": round(avg_epsilon, 4),
                    "avg_q_table_size": round(avg_q_size, 1),
                    "total_learners": count,
                    "total_replay_entries": sum(len(l.replay) for l in self.learners.values()),
                },
            ))

    def get_agent_stats(self, agent_id: str) -> dict | None:
        learner = self.learners.get(agent_id)
        if not learner:
            return None
        return {
            "q_table_size": len(learner.q_table),
            "total_updates": learner.total_updates,
            "epsilon": round(learner.epsilon, 4),
            "learning_rate": round(learner.learning_rate, 6),
            "replay_buffer_size": len(learner.replay),
        }

    def inherit_knowledge(self, parent_a_id: str, parent_b_id: str, child_id: str,
                          inheritance_rate: float = 0.3):
        """Transfer partial Q-table knowledge from parents to child.

        Called by reproduction system when a child is born.
        Child inherits a blend of both parents' Q-values, weighted
        by inheritance_rate. This simulates "cultural knowledge transfer".
        """
        parent_a = self.learners.get(parent_a_id)
        parent_b = self.learners.get(parent_b_id)
        child = self._ensure_learner(child_id)

        if not parent_a and not parent_b:
            return

        # Blend parent Q-tables
        all_states = set()
        if parent_a:
            all_states.update(parent_a.q_table.keys())
        if parent_b:
            all_states.update(parent_b.q_table.keys())

        for state in all_states:
            q_a = parent_a.q_table.get(state, {}) if parent_a else {}
            q_b = parent_b.q_table.get(state, {}) if parent_b else {}
            all_actions = set(q_a.keys()) | set(q_b.keys())

            child.q_table[state] = {}
            for action in all_actions:
                val_a = q_a.get(action, 0.0)
                val_b = q_b.get(action, 0.0)
                blended = (val_a + val_b) / 2.0
                child.q_table[state][action] = blended * inheritance_rate
