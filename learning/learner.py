"""Q-learning based agent learner for AI Agent City."""

from __future__ import annotations

import random
from typing import Optional

from agents.agent import Action, ActionType, Agent
from learning.memory import AgentMemory
from learning.replay import PrioritizedReplayBuffer


def discretize_state(agent: Agent) -> tuple:
    """Convert agent's continuous state into a discrete tuple for Q-table lookup."""
    energy_level = "low" if agent.energy < 30 else "mid" if agent.energy < 70 else "high"
    inventory_level = "empty" if agent.inventory.total == 0 else "some" if agent.inventory.total < 10 else "full"
    has_neighbors = len(agent.perception.get("nearby_agents", [])) > 0 if isinstance(agent.perception, dict) else False
    time_of_day = agent.perception.get("time_of_day", "day") if isinstance(agent.perception, dict) else "day"
    mood_level = "low" if agent.mood < 0.3 else "mid" if agent.mood < 0.7 else "high"

    # Check for resources on current tile
    has_resources = False
    if isinstance(agent.perception, dict):
        for tile in agent.perception.get("tiles", []):
            if hasattr(tile, "x") and tile.x == agent.x and tile.y == agent.y:
                has_resources = tile.total_resources() > 0
                break

    return (energy_level, inventory_level, has_neighbors, time_of_day, mood_level, has_resources)


LEARNABLE_ACTIONS = [
    ActionType.MOVE,
    ActionType.GATHER,
    ActionType.REST,
    ActionType.TRADE,
    ActionType.COMMUNICATE,
    ActionType.WORK,
    ActionType.LEARN,
]


class AgentLearner:
    """Q-learning based decision maker for agents."""

    def __init__(
        self,
        agent_id: str,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon_start: float = 0.3,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        replay_capacity: int = 500,
        replay_batch_size: int = 16,
        replay_every: int = 5,
        seed: int = 42,
    ):
        self.agent_id = agent_id
        self.q_table: dict[tuple, dict[str, float]] = {}
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon_start
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self._rng = random.Random(seed)
        self.memory = AgentMemory()

        # Experience replay
        self.replay_buffer = PrioritizedReplayBuffer(capacity=replay_capacity, seed=seed)
        self.replay_batch_size = replay_batch_size
        self.replay_every = replay_every

        # Learning rate scheduling
        self._base_learning_rate = learning_rate
        self._lr_decay = 0.9999
        self._lr_min = 0.001

        # Tracking
        self.total_updates = 0
        self.replay_updates = 0
        self.last_state: Optional[tuple] = None
        self.last_action: Optional[ActionType] = None

    def choose_action(self, agent: Agent) -> Action:
        """Epsilon-greedy action selection."""
        state = discretize_state(agent)
        available = self._get_available_actions(agent)

        if self._rng.random() < self.epsilon:
            # Explore: random action, biased by personality
            action_type = self._personality_biased_random(agent, available)
        else:
            # Exploit: best known action
            q_values = self.q_table.get(state, {})
            action_type = max(available, key=lambda a: q_values.get(a.value, 0.0))

        self.last_state = state
        self.last_action = action_type

        # Build action with context
        action = Action(type=action_type)
        if action_type == ActionType.MOVE:
            action = self._plan_move(agent)
        elif action_type == ActionType.TRADE:
            action.target = self._pick_trade_partner(agent)

        return action

    def update(self, agent: Agent, reward: float):
        """Update Q-values based on reward received, then replay past experiences."""
        if self.last_state is None or self.last_action is None:
            return

        current_state = self.last_state
        action = self.last_action.value
        next_state = discretize_state(agent)

        # Q-learning update for current transition
        new_q = self._update_q(current_state, action, reward, next_state)

        # Store transition in replay buffer
        self.replay_buffer.push(current_state, action, reward, next_state, agent.age)

        # Periodic experience replay
        if self.total_updates % self.replay_every == 0 and len(self.replay_buffer) >= self.replay_batch_size:
            self._replay()

        # Decay exploration and learning rate
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.learning_rate = max(self._lr_min, self.learning_rate * self._lr_decay)
        self.total_updates += 1

        # Record in memory
        importance = min(1.0, abs(reward) / 3.0)
        self.memory.record(
            tick=agent.age,
            event_type="reward",
            data={
                "state": current_state,
                "action": action,
                "reward": reward,
                "new_q": round(new_q, 3),
            },
            importance=importance,
        )

    def _update_q(self, state: tuple, action: str, reward: float, next_state: tuple) -> float:
        """Single Q-value update. Returns the new Q-value."""
        current_q = self.q_table.setdefault(state, {}).get(action, 0.0)
        next_q_values = self.q_table.get(next_state, {})
        next_max = max(next_q_values.values(), default=0.0)

        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max - current_q
        )
        self.q_table[state][action] = new_q
        return new_q

    def _replay(self):
        """Replay a batch of past experiences to accelerate learning."""
        batch = self.replay_buffer.sample(self.replay_batch_size)
        for transition in batch:
            self._update_q(
                transition.state, transition.action,
                transition.reward, transition.next_state,
            )
        self.replay_updates += len(batch)

    def _get_available_actions(self, agent: Agent) -> list[ActionType]:
        """Filter actions based on what's actually possible."""
        available = []
        for action in LEARNABLE_ACTIONS:
            if action == ActionType.GATHER:
                if not agent.inventory.is_full:
                    available.append(action)
            elif action == ActionType.TRADE or action == ActionType.COMMUNICATE:
                if isinstance(agent.perception, dict) and agent.perception.get("nearby_agents"):
                    available.append(action)
            elif action == ActionType.REST:
                available.append(action)
            else:
                available.append(action)
        if not available:
            available = [ActionType.MOVE, ActionType.REST]
        return available

    def _personality_biased_random(self, agent: Agent, available: list[ActionType]) -> ActionType:
        """Random selection weighted by personality traits."""
        weights = {}
        p = agent.personality
        for a in available:
            w = 1.0
            if a == ActionType.MOVE:
                w += p.curiosity * 2
            elif a == ActionType.GATHER:
                w += p.industriousness * 2
            elif a == ActionType.TRADE:
                w += p.sociability * 1.5
            elif a == ActionType.COMMUNICATE:
                w += p.sociability * 2
            elif a == ActionType.WORK:
                w += p.industriousness * 2.5
            elif a == ActionType.REST:
                w += (1.0 - p.industriousness) * 1.5
            elif a == ActionType.LEARN:
                w += p.curiosity * 2
            weights[a] = w

        total = sum(weights.values())
        r = self._rng.random() * total
        cumulative = 0.0
        for action, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return action
        return available[-1]

    def _plan_move(self, agent: Agent) -> Action:
        """Plan movement — explore unknown areas or move toward resources."""
        # Check memory for known resource locations
        known_resources = self.memory.long_term.recall_by_type("resource_found", limit=3)
        if known_resources and self._rng.random() < 0.3:
            target_data = known_resources[0].data
            return Action(
                type=ActionType.MOVE,
                target=(target_data.get("x"), target_data.get("y")),
            )
        return Action(type=ActionType.MOVE)

    def _pick_trade_partner(self, agent: Agent) -> Optional[str]:
        """Pick a trade partner, preferring trusted agents."""
        if not isinstance(agent.perception, dict):
            return None
        nearby = agent.perception.get("nearby_agents", [])
        if not nearby:
            return None
        # Prefer agents we trust
        trusted = [(aid, agent.trust.get(aid, 0.5)) for aid in nearby]
        trusted.sort(key=lambda x: x[1], reverse=True)
        return trusted[0][0]

    def get_stats(self) -> dict:
        return {
            "q_table_size": len(self.q_table),
            "total_updates": self.total_updates,
            "replay_updates": self.replay_updates,
            "replay_buffer_size": len(self.replay_buffer),
            "epsilon": round(self.epsilon, 4),
            "memory_size": {
                "working": len(self.memory.working),
                "short_term": len(self.memory.short_term),
                "long_term": len(self.memory.long_term),
            },
        }


class SocialLearner:
    """Enables agents to learn from observing other agents' success."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def observe_and_learn(
        self,
        observer: Agent,
        observer_learner: AgentLearner,
        neighbors: dict[str, Agent],
        neighbor_learners: dict[str, AgentLearner],
    ):
        """Observer copies strategies from successful neighbors."""
        if not neighbors:
            return

        # Find the most successful neighbor
        best_neighbor = max(neighbors.values(), key=lambda a: a.total_reward)

        if best_neighbor.total_reward <= observer.total_reward:
            return  # nothing to learn

        # Trust check — only learn from trusted agents
        trust = observer.trust.get(best_neighbor.id, 0.5)
        if self._rng.random() > trust:
            return

        # Copy some Q-values from the successful neighbor
        best_learner = neighbor_learners.get(best_neighbor.id)
        if not best_learner:
            return

        copy_rate = 0.1 * trust  # more trusted = more copying
        for state, actions in best_learner.q_table.items():
            if state not in observer_learner.q_table:
                observer_learner.q_table[state] = {}
            for action, q_val in actions.items():
                current = observer_learner.q_table[state].get(action, 0.0)
                observer_learner.q_table[state][action] = current + copy_rate * (q_val - current)

        # Record in memory
        observer_learner.memory.record(
            tick=observer.age,
            event_type="social_learning",
            data={
                "learned_from": best_neighbor.id,
                "learned_from_name": best_neighbor.name,
                "their_reward": best_neighbor.total_reward,
                "trust": trust,
            },
            importance=0.6,
        )


class KnowledgeSharer:
    """Gossip protocol — agents share facts during communication."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def share_knowledge(
        self,
        speaker: Agent,
        speaker_memory: AgentMemory,
        listener: Agent,
        listener_memory: AgentMemory,
    ):
        """Speaker shares known facts with listener."""
        # Share resource locations
        for key, value in speaker_memory.long_term.facts.items():
            if key.startswith("location:"):
                trust = listener.trust.get(speaker.id, 0.5)
                if self._rng.random() < trust:
                    listener_memory.long_term.store_fact(key, value)

        # Share agent information
        for key, value in speaker_memory.long_term.facts.items():
            if key.startswith("agent:"):
                trust = listener.trust.get(speaker.id, 0.5)
                if self._rng.random() < trust * 0.5:
                    listener_memory.long_term.store_fact(key, value)
