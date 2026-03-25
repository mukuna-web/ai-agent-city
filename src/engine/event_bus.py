"""Event bus for simulation-wide event dispatch and handling."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any
from collections import defaultdict


@dataclass(frozen=True)
class Event:
    """Immutable simulation event."""
    tick: int
    event_type: str
    data: dict[str, Any]
    source_agent_id: str | None = None
    target_agent_id: str | None = None
    district_id: str | None = None

    def __repr__(self) -> str:
        return f"Event(t={self.tick}, {self.event_type}, src={self.source_agent_id})"


EventHandler = Callable[[Event], None]


class EventBus:
    """
    Publish/subscribe event bus for the simulation.

    All state changes flow through events. This enables:
    - Deterministic replay (just replay events)
    - Decoupled systems (economy doesn't import social)
    - Observable simulation (UI subscribes to events)
    - Audit logging
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._event_log: list[Event] = []
        self._log_enabled: bool = True

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to ALL events (for logging, UI, replay)."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        """Dispatch event to all subscribed handlers."""
        if self._log_enabled:
            self._event_log.append(event)

        # Type-specific handlers
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error for {event.event_type}: {e}")

        # Global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Global handler error: {e}")

    def emit_many(self, events: list[Event]) -> None:
        """Dispatch multiple events in order."""
        for event in events:
            self.emit(event)

    def get_log(self, since_tick: int | None = None, event_type: str | None = None) -> list[Event]:
        """Query the event log."""
        log = self._event_log
        if since_tick is not None:
            log = [e for e in log if e.tick >= since_tick]
        if event_type is not None:
            log = [e for e in log if e.event_type == event_type]
        return log

    def get_log_size(self) -> int:
        return len(self._event_log)

    def clear_log(self) -> None:
        """Clear the event log (for memory management)."""
        self._event_log.clear()

    def truncate_log(self, keep_last_n: int) -> None:
        """Keep only the last N events."""
        if len(self._event_log) > keep_last_n:
            self._event_log = self._event_log[-keep_last_n:]
