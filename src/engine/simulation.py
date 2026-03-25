"""
AI Agent City — Main Simulation Engine

The simulation loop that orchestrates all systems each tick.
Follows the tiered update schedule from the architecture doc.
"""

from __future__ import annotations
import time
from typing import Any

from .event_bus import EventBus, Event
from .world_state import WorldState


class SimulationEngine:
    """
    Core simulation loop. Orchestrates all subsystems.

    Update frequencies:
    - EVERY TICK:      Agent reactive cognition, need decay, movement
    - EVERY 10 TICKS:  Agent deliberation, social interactions
    - EVERY 100 TICKS: Agent strategic thinking, market order matching,
                       economic indicators, construction progress
    - EVERY 1000 TICKS: Population updates (births/deaths), labor market
                        rebalancing, memory compaction, season changes
    """

    def __init__(self, world: WorldState, event_bus: EventBus | None = None) -> None:
        self.world = world
        self.event_bus = event_bus or EventBus()
        self._running = False
        self._systems: list[tuple[str, int, Any]] = []  # (name, frequency, system)
        self._tick_callbacks: list[Any] = []

    def register_system(self, name: str, frequency: int, system: Any) -> None:
        """
        Register a subsystem to run at a given frequency.

        Args:
            name: Human-readable system name
            frequency: Run every N ticks (1=every tick, 10=every 10 ticks, etc.)
            system: Object with an update(world, tick, event_bus) method
        """
        self._systems.append((name, frequency, system))
        self._systems.sort(key=lambda s: s[1])  # Run frequent systems first

    def on_tick(self, callback: Any) -> None:
        """Register a callback that fires after every tick."""
        self._tick_callbacks.append(callback)

    def run(self, ticks: int, target_tps: float = 10.0) -> None:
        """
        Run the simulation for a fixed number of ticks.

        Args:
            ticks: Number of ticks to simulate
            target_tps: Target ticks per second (0 = unlimited)
        """
        self._running = True
        tick_duration = 1.0 / target_tps if target_tps > 0 else 0
        start_tick = self.world.current_tick

        for i in range(ticks):
            if not self._running:
                break

            tick_start = time.perf_counter()
            self._run_tick()
            tick_elapsed = time.perf_counter() - tick_start

            # Rate limiting
            if tick_duration > 0 and tick_elapsed < tick_duration:
                time.sleep(tick_duration - tick_elapsed)

        elapsed_total = self.world.current_tick - start_tick
        print(f"[Simulation] Ran {elapsed_total} ticks")

    def run_until(self, condition: Any, max_ticks: int = 1_000_000) -> int:
        """Run until a condition is met or max ticks reached."""
        self._running = True
        ticks_run = 0

        while self._running and ticks_run < max_ticks:
            self._run_tick()
            ticks_run += 1
            if condition(self.world):
                break

        return ticks_run

    def step(self) -> None:
        """Run a single tick. Useful for debugging."""
        self._run_tick()

    def pause(self) -> None:
        """Pause the simulation."""
        self._running = False

    def _run_tick(self) -> None:
        """Execute one simulation tick."""
        tick = self.world.current_tick

        # Emit tick start event
        self.event_bus.emit(Event(
            tick=tick,
            event_type="tick.start",
            data={"population": self.world.population_count()},
        ))

        # Run all registered systems at their scheduled frequency
        for name, frequency, system in self._systems:
            if tick % frequency == 0:
                try:
                    system.update(self.world, tick, self.event_bus)
                except Exception as e:
                    print(f"[Simulation] Error in {name} at tick {tick}: {e}")
                    self.event_bus.emit(Event(
                        tick=tick,
                        event_type="system.error",
                        data={"system": name, "error": str(e)},
                    ))

        # Emit tick end event
        self.event_bus.emit(Event(
            tick=tick,
            event_type="tick.end",
            data={},
        ))

        # Fire callbacks
        for callback in self._tick_callbacks:
            try:
                callback(self.world, tick)
            except Exception as e:
                print(f"[Simulation] Callback error at tick {tick}: {e}")

        # Advance tick
        self.world.current_tick += 1

        # Periodic memory management
        if tick % 10000 == 0 and tick > 0:
            self.event_bus.truncate_log(keep_last_n=50000)

    def get_stats(self) -> dict:
        """Current simulation statistics."""
        return {
            "tick": self.world.current_tick,
            "population": self.world.population_count(),
            "adults": self.world.adult_count(),
            "children": self.world.child_count(),
            "buildings": len(self.world.buildings),
            "firms": len(self.world.firms),
            "events_logged": self.event_bus.get_log_size(),
            "running": self._running,
        }
