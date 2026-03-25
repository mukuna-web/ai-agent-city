"""Experience Replay Buffer for improved Q-learning convergence.

Stores past (state, action, reward, next_state) transitions and replays
them in random mini-batches, breaking temporal correlations and allowing
agents to learn from rare but important experiences multiple times.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class Transition:
    state: tuple
    action: str
    reward: float
    next_state: tuple
    tick: int


class ReplayBuffer:
    """Fixed-size circular buffer of past transitions."""

    def __init__(self, capacity: int = 1000, seed: int = 42):
        self.capacity = capacity
        self.buffer: deque[Transition] = deque(maxlen=capacity)
        self._rng = random.Random(seed)

    def push(self, state: tuple, action: str, reward: float, next_state: tuple, tick: int):
        self.buffer.append(Transition(
            state=state, action=action, reward=reward,
            next_state=next_state, tick=tick,
        ))

    def sample(self, batch_size: int) -> list[Transition]:
        """Sample a random mini-batch of transitions."""
        batch_size = min(batch_size, len(self.buffer))
        return self._rng.sample(list(self.buffer), batch_size)

    def __len__(self) -> int:
        return len(self.buffer)


class PrioritizedReplayBuffer:
    """Replay buffer that samples high-reward transitions more often.

    Transitions with larger absolute rewards are sampled with higher
    probability, so agents learn faster from significant events like
    successful trades or dangerous situations.
    """

    def __init__(self, capacity: int = 1000, alpha: float = 0.6, seed: int = 42):
        self.capacity = capacity
        self.alpha = alpha  # prioritization exponent (0 = uniform, 1 = full priority)
        self.buffer: deque[Transition] = deque(maxlen=capacity)
        self.priorities: deque[float] = deque(maxlen=capacity)
        self._rng = random.Random(seed)

    def push(self, state: tuple, action: str, reward: float, next_state: tuple, tick: int):
        priority = (abs(reward) + 0.01) ** self.alpha
        self.buffer.append(Transition(
            state=state, action=action, reward=reward,
            next_state=next_state, tick=tick,
        ))
        self.priorities.append(priority)

    def sample(self, batch_size: int) -> list[Transition]:
        """Weighted sampling — high-reward transitions are picked more often."""
        batch_size = min(batch_size, len(self.buffer))
        if batch_size == 0:
            return []

        priority_list = list(self.priorities)
        total = sum(priority_list)
        if total == 0:
            return self._rng.sample(list(self.buffer), batch_size)

        weights = [p / total for p in priority_list]
        indices = []
        buffer_list = list(self.buffer)

        # Weighted sampling without replacement
        remaining_weights = list(weights)
        remaining_indices = list(range(len(buffer_list)))
        for _ in range(batch_size):
            if not remaining_indices:
                break
            total_w = sum(remaining_weights)
            if total_w == 0:
                break
            r = self._rng.random() * total_w
            cumulative = 0.0
            for i, (idx, w) in enumerate(zip(remaining_indices, remaining_weights)):
                cumulative += w
                if r <= cumulative:
                    indices.append(idx)
                    remaining_indices.pop(i)
                    remaining_weights.pop(i)
                    break

        return [buffer_list[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)
