"""Production system — firms produce goods using workers. Runs every 10 ticks."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.world_state import WorldState
    from ..engine.event_bus import EventBus


class ProductionUpdateSystem:
    """
    Run production for all operational firms.
    Workers earn wages, firms earn revenue, goods are produced.
    Frequency: 10 (every 10 ticks).
    """

    def update(self, world: "WorldState", tick: int, event_bus: "EventBus") -> None:
        from ..engine.event_bus import Event

        for firm_id, firm in list(world.firms.items()):
            workers = [world.agents[wid] for wid in firm.employees if wid in world.agents]
            alive_workers = [w for w in workers if w.biology.is_alive]

            if not alive_workers:
                continue

            # Pay wages
            for worker in alive_workers:
                wage = worker.economy.wage
                if world.ledger and wage > 0:
                    tx = world.ledger.transfer(
                        firm_id, worker.identity.agent_id, wage * 10,  # 10 ticks worth
                        "wage", tick, f"Wage for {worker.economy.profession}"
                    )
                    if tx:
                        # Satisfy economic needs
                        new_agent = worker.with_needs(worker.needs.satisfy("food", 0.15))
                        new_agent = new_agent.with_needs(new_agent.needs.satisfy("shelter", 0.1))
                        world.agents[worker.identity.agent_id] = new_agent

            # Produce goods (simplified — full production uses ProductionSystem)
            event_bus.emit(Event(
                tick=tick,
                event_type="firm.produced",
                data={"firm_id": firm_id, "workers": len(alive_workers)},
            ))
