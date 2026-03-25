"""Event system for random world events in AI Agent City."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Event:
    type: str  # "weather", "market_crash", "bounty", "festival", "drought"
    name: str
    tick_start: int
    duration: int
    affected_area: Optional[tuple[int, int, int]] = None  # x, y, radius (None = global)
    effects: dict[str, float] = field(default_factory=dict)

    @property
    def tick_end(self) -> int:
        return self.tick_start + self.duration

    def is_active(self, tick: int) -> bool:
        return self.tick_start <= tick < self.tick_end

    def affects_position(self, x: int, y: int) -> bool:
        if self.affected_area is None:
            return True
        ax, ay, radius = self.affected_area
        return abs(x - ax) <= radius and abs(y - ay) <= radius


EVENT_TEMPLATES = [
    {"type": "weather", "name": "Heavy Rain", "duration": 6,
     "effects": {"movement_cost": 1.5, "gather_rate": 0.7, "mood": -0.1}},
    {"type": "weather", "name": "Sunny Day", "duration": 12,
     "effects": {"gather_rate": 1.3, "mood": 0.1}},
    {"type": "economic", "name": "Market Boom", "duration": 24,
     "effects": {"price_multiplier": 1.5, "trade_bonus": 0.2}},
    {"type": "economic", "name": "Market Crash", "duration": 12,
     "effects": {"price_multiplier": 0.5, "trade_bonus": -0.2}},
    {"type": "disaster", "name": "Drought", "duration": 48,
     "effects": {"food_regen": 0.0, "mood": -0.3}},
    {"type": "social", "name": "Festival", "duration": 6,
     "effects": {"social_bonus": 0.5, "mood": 0.3, "work_rate": 0.5}},
    {"type": "discovery", "name": "Resource Vein Found", "duration": 1,
     "effects": {"stone_bonus": 5}},
]


class EventManager:
    def __init__(self, seed: int = 42):
        self.active_events: list[Event] = []
        self.event_history: list[Event] = []
        self._rng = random.Random(seed)

    def check_random_events(self, tick: int, world_width: int, world_height: int) -> list[Event]:
        new_events = []
        if self._rng.random() < 0.02:  # 2% chance per tick
            template = self._rng.choice(EVENT_TEMPLATES)
            area = None
            if template["type"] in ("disaster", "discovery"):
                area = (
                    self._rng.randint(0, world_width - 1),
                    self._rng.randint(0, world_height - 1),
                    self._rng.randint(3, 10),
                )
            event = Event(
                type=template["type"],
                name=template["name"],
                tick_start=tick,
                duration=template["duration"],
                affected_area=area,
                effects=dict(template["effects"]),
            )
            new_events.append(event)
            self.active_events.append(event)
            self.event_history.append(event)
        return new_events

    def get_active_events(self, tick: int) -> list[Event]:
        self.active_events = [e for e in self.active_events if e.is_active(tick)]
        return self.active_events

    def get_effects_at(self, tick: int, x: int, y: int) -> dict[str, float]:
        combined: dict[str, float] = {}
        for event in self.get_active_events(tick):
            if event.affects_position(x, y):
                for key, value in event.effects.items():
                    if key in combined:
                        combined[key] += value
                    else:
                        combined[key] = value
        return combined
