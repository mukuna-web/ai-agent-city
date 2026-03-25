"""Status reporter — prints simulation state periodically. Every 100 ticks."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class StatusReporterSystem:
    """
    Print simulation statistics to console.
    Frequency: 100 (every 100 ticks).
    """

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        agents = world.get_alive_agents()
        if not agents:
            print(f"  Tick {tick:>6d} | POPULATION EXTINCT")
            return

        pop = len(agents)
        adults = len([a for a in agents if a.biology.lifecycle_stage in ("adult", "elder")])
        children = len([a for a in agents if a.biology.lifecycle_stage in ("child", "adolescent")])
        avg_food = sum(a.needs.food for a in agents) / pop
        avg_health = sum(a.biology.health for a in agents) / pop
        employed = len([a for a in agents if a.economy.employer_id])
        avg_cash = sum(a.economy.cash for a in agents) / pop

        print(
            f"  Tick {tick:>6d} | Pop: {pop:>4d} (A:{adults} C:{children}) | "
            f"Food: {avg_food:.2f} | Health: {avg_health:.2f} | "
            f"Employed: {employed} | Avg Cash: {avg_cash:.0f}₵"
        )
