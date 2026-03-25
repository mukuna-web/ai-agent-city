"""Base Agent class for AI Agent City."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AgentState(Enum):
    IDLE = "idle"
    WORKING = "working"
    TRADING = "trading"
    RESTING = "resting"
    EXPLORING = "exploring"
    GATHERING = "gathering"
    LEARNING = "learning"
    COMMUNICATING = "communicating"


class ActionType(Enum):
    MOVE = "move"
    GATHER = "gather"
    TRADE = "trade"
    BUILD = "build"
    REST = "rest"
    LEARN = "learn"
    COMMUNICATE = "communicate"
    WORK = "work"
    IDLE = "idle"


ACTION_COSTS = {
    ActionType.MOVE: 1,
    ActionType.GATHER: 2,
    ActionType.TRADE: 1,
    ActionType.BUILD: 3,
    ActionType.REST: 1,
    ActionType.LEARN: 2,
    ActionType.COMMUNICATE: 1,
    ActionType.WORK: 2,
    ActionType.IDLE: 0,
}


@dataclass
class Personality:
    curiosity: float = 0.5      # exploration tendency
    aggression: float = 0.3     # conflict preference
    sociability: float = 0.5    # interaction preference
    industriousness: float = 0.5  # work ethic

    @classmethod
    def random(cls, rng: random.Random) -> Personality:
        return cls(
            curiosity=round(rng.uniform(0.1, 0.9), 2),
            aggression=round(rng.uniform(0.0, 0.7), 2),
            sociability=round(rng.uniform(0.1, 0.9), 2),
            industriousness=round(rng.uniform(0.2, 0.9), 2),
        )


@dataclass
class Inventory:
    items: dict[str, int] = field(default_factory=dict)
    capacity: int = 20

    @property
    def total(self) -> int:
        return sum(self.items.values())

    @property
    def is_full(self) -> bool:
        return self.total >= self.capacity

    def add(self, item: str, quantity: int = 1) -> int:
        space = self.capacity - self.total
        actual = min(quantity, space)
        if actual > 0:
            self.items[item] = self.items.get(item, 0) + actual
        return actual

    def remove(self, item: str, quantity: int = 1) -> int:
        available = self.items.get(item, 0)
        actual = min(quantity, available)
        if actual > 0:
            self.items[item] -= actual
            if self.items[item] <= 0:
                del self.items[item]
        return actual

    def has(self, item: str, quantity: int = 1) -> bool:
        return self.items.get(item, 0) >= quantity

    def __repr__(self) -> str:
        return str(self.items)


@dataclass
class Action:
    type: ActionType
    target: Any = None  # position tuple, agent_id, resource name, etc.
    params: dict = field(default_factory=dict)

    @property
    def cost(self) -> int:
        return ACTION_COSTS.get(self.type, 1)


class Agent:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        personality: Optional[Personality] = None,
        seed: int = 42,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.x = x
        self.y = y
        self._rng = random.Random(seed)
        self.personality = personality or Personality.random(self._rng)
        self.inventory = Inventory()
        self.state = AgentState.IDLE
        self.energy: float = 100.0
        self.max_energy: float = 100.0
        self.coins: int = 50
        self.action_points: int = 5
        self.max_action_points: int = 5
        self.mood: float = 0.5  # 0.0 = miserable, 1.0 = ecstatic
        self.age: int = 0  # ticks alive
        self.skills: dict[str, float] = {
            "foraging": 0.1,
            "crafting": 0.1,
            "trading": 0.1,
            "building": 0.1,
            "socializing": 0.1,
        }
        self.skill_xp: dict[str, int] = {k: 0 for k in self.skills}
        self.trust: dict[str, float] = {}  # agent_id -> trust score
        self.knowledge: list[dict] = []  # learned facts
        self.perception: list[Any] = []  # what agent sees this tick
        self.last_action: Optional[Action] = None
        self.last_reward: float = 0.0
        self.total_reward: float = 0.0

    @property
    def position(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def is_alive(self) -> bool:
        return self.energy > 0

    @property
    def is_tired(self) -> bool:
        return self.energy < 30

    @property
    def can_act(self) -> bool:
        return self.action_points > 0 and self.is_alive

    def perceive(self, visible_tiles: list, nearby_agents: list[str], events: dict):
        self.perception = {
            "tiles": visible_tiles,
            "nearby_agents": nearby_agents,
            "events": events,
            "energy": self.energy,
            "inventory": dict(self.inventory.items),
            "coins": self.coins,
            "position": self.position,
            "time_of_day": None,  # set by engine
            "mood": self.mood,
        }

    def decide(self) -> Action:
        """Default random decision — overridden by learning system."""
        if self.is_tired:
            return Action(ActionType.REST)
        actions = list(ActionType)
        return Action(self._rng.choice(actions))

    def execute_action(self, action: Action) -> bool:
        if action.cost > self.action_points:
            return False
        self.action_points -= action.cost
        self.last_action = action
        self.energy -= action.cost * 0.5  # actions cost a little energy
        return True

    def rest(self):
        recovery = 25.0
        self.energy = min(self.max_energy, self.energy + recovery)
        self.mood = min(1.0, self.mood + 0.05)
        self.state = AgentState.RESTING

    def reset_tick(self):
        self.action_points = self.max_action_points
        self.age += 1
        # Natural energy drain (very slow)
        self.energy = max(0, self.energy - 0.3)
        # Passive energy recovery when not acting
        if self.state == AgentState.IDLE:
            self.energy = min(self.max_energy, self.energy + 2)
        # Mood decay toward neutral
        if self.mood > 0.5:
            self.mood -= 0.01
        elif self.mood < 0.5:
            self.mood += 0.01

    def gain_skill_xp(self, skill: str, amount: int):
        if skill not in self.skills:
            return
        self.skill_xp[skill] += amount
        threshold = 100 + int(self.skills[skill] * 20) * 50
        if self.skill_xp[skill] >= threshold:
            self.skills[skill] = min(1.0, self.skills[skill] + 0.05)
            self.skill_xp[skill] = 0

    def skill_check(self, skill: str, difficulty: float = 0.5) -> bool:
        proficiency = self.skills.get(skill, 0.0)
        return self._rng.random() < proficiency / difficulty

    def update_trust(self, other_id: str, delta: float):
        current = self.trust.get(other_id, 0.5)
        self.trust[other_id] = max(0.0, min(1.0, current + delta))

    def receive_reward(self, reward: float):
        self.last_reward = reward
        self.total_reward += reward

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "state": self.state.value,
            "energy": round(self.energy, 1),
            "coins": self.coins,
            "mood": round(self.mood, 2),
            "inventory": dict(self.inventory.items),
            "skills": {k: round(v, 2) for k, v in self.skills.items()},
            "total_reward": round(self.total_reward, 1),
            "age": self.age,
        }

    def __repr__(self) -> str:
        return f"Agent({self.name}, pos={self.position}, energy={self.energy:.0f}, state={self.state.value})"
