"""Memory architecture for AI agents — working, short-term, and long-term memory."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MemoryEntry:
    tick: int
    event_type: str  # "action", "observation", "trade", "communication", "reward"
    data: dict
    importance: float = 0.5  # 0.0-1.0, affects retention

    def __repr__(self) -> str:
        return f"Memory(t={self.tick}, {self.event_type}, imp={self.importance:.1f})"


class WorkingMemory:
    """Immediate context for current tick decisions. Cleared each tick."""

    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.items: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry):
        self.items.append(entry)
        if len(self.items) > self.capacity:
            # Drop least important
            self.items.sort(key=lambda e: e.importance, reverse=True)
            self.items = self.items[: self.capacity]

    def clear(self):
        self.items.clear()

    def get_context(self) -> list[dict]:
        return [e.data for e in self.items]

    def __len__(self) -> int:
        return len(self.items)


class ShortTermMemory:
    """Recent events over last N ticks. Ring buffer."""

    def __init__(self, capacity: int = 100, tick_window: int = 50):
        self.capacity = capacity
        self.tick_window = tick_window
        self.buffer: deque[MemoryEntry] = deque(maxlen=capacity)

    def add(self, entry: MemoryEntry):
        self.buffer.append(entry)

    def recall(self, current_tick: int, event_type: Optional[str] = None) -> list[MemoryEntry]:
        cutoff = current_tick - self.tick_window
        results = [e for e in self.buffer if e.tick >= cutoff]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        return results

    def recall_recent(self, n: int = 10) -> list[MemoryEntry]:
        return list(self.buffer)[-n:]

    def count_type(self, event_type: str, current_tick: int) -> int:
        return len(self.recall(current_tick, event_type))

    def __len__(self) -> int:
        return len(self.buffer)


class LongTermMemory:
    """Persistent storage for learned knowledge and important memories."""

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self.memories: list[MemoryEntry] = []
        self.facts: dict[str, Any] = {}  # key-value knowledge store

    def store(self, entry: MemoryEntry):
        if entry.importance >= 0.7:  # only store important memories
            self.memories.append(entry)
            self._prune()

    def store_fact(self, key: str, value: Any):
        self.facts[key] = value

    def recall_fact(self, key: str) -> Optional[Any]:
        return self.facts.get(key)

    def recall_by_type(self, event_type: str, limit: int = 10) -> list[MemoryEntry]:
        matches = [m for m in self.memories if m.event_type == event_type]
        matches.sort(key=lambda e: e.importance, reverse=True)
        return matches[:limit]

    def recall_all(self, limit: int = 20) -> list[MemoryEntry]:
        sorted_mem = sorted(self.memories, key=lambda e: e.importance, reverse=True)
        return sorted_mem[:limit]

    def _prune(self):
        if len(self.memories) > self.max_entries:
            self.memories.sort(key=lambda e: e.importance, reverse=True)
            self.memories = self.memories[: self.max_entries]

    def __len__(self) -> int:
        return len(self.memories)


class AgentMemory:
    """Unified memory system combining all three tiers."""

    def __init__(self):
        self.working = WorkingMemory(capacity=10)
        self.short_term = ShortTermMemory(capacity=100, tick_window=50)
        self.long_term = LongTermMemory(max_entries=500)

    def record(self, tick: int, event_type: str, data: dict, importance: float = 0.5):
        entry = MemoryEntry(tick=tick, event_type=event_type, data=data, importance=importance)
        self.working.add(entry)
        self.short_term.add(entry)
        if importance >= 0.7:
            self.long_term.store(entry)

    def start_new_tick(self):
        self.working.clear()

    def get_decision_context(self, current_tick: int) -> dict:
        return {
            "working": self.working.get_context(),
            "recent": [e.data for e in self.short_term.recall_recent(5)],
            "important": [e.data for e in self.long_term.recall_all(5)],
            "facts": dict(self.long_term.facts),
        }

    def remember_location(self, name: str, x: int, y: int):
        self.long_term.store_fact(f"location:{name}", (x, y))

    def recall_location(self, name: str) -> Optional[tuple[int, int]]:
        return self.long_term.recall_fact(f"location:{name}")

    def remember_agent(self, agent_id: str, info: dict):
        self.long_term.store_fact(f"agent:{agent_id}", info)

    def recall_agent(self, agent_id: str) -> Optional[dict]:
        return self.long_term.recall_fact(f"agent:{agent_id}")
