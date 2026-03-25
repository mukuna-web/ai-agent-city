"""
AI Agent City — Main Entry Point

Bootstraps the simulation with a founding population and runs it.
"""

from __future__ import annotations
import argparse
import random
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Agent City — Civilization Simulator")
    parser.add_argument("--population", type=int, default=50, help="Initial population size")
    parser.add_argument("--ticks", type=int, default=1000, help="Number of ticks to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--tps", type=float, default=10.0, help="Target ticks per second (0=unlimited)")
    parser.add_argument("--map-size", type=int, default=64, help="Map width/height in tiles")
    parser.add_argument("--verbose", action="store_true", help="Print detailed tick info")
    args = parser.parse_args()

    random.seed(args.seed)
    print(f"\n🏙️  AI Agent City v0.1.0")
    print(f"   Seed: {args.seed}")
    print(f"   Population: {args.population}")
    print(f"   Map: {args.map_size}x{args.map_size}")
    print(f"   Ticks: {args.ticks}")
    print(f"   Target TPS: {args.tps}")
    print()

    # Import here to avoid circular imports during module loading
    from .engine.event_bus import EventBus, Event
    from .engine.world_state import WorldState
    from .engine.simulation import SimulationEngine

    # Initialize world
    world = WorldState(seed=args.seed)
    event_bus = EventBus()

    # Create founding population
    try:
        from .agents.factory import create_founder_population
        founders = create_founder_population(args.population, tick=0)
        for agent in founders:
            world.agents[agent.identity.agent_id] = agent
        print(f"✅ Created {len(founders)} founding agents")
    except ImportError as e:
        print(f"⚠️  Agent module not ready: {e}")
        print("   Running in skeleton mode (no agents)")

    # Initialize simulation engine
    engine = SimulationEngine(world, event_bus)

    # Register basic systems (more will be added as modules are built)
    # For now, register a simple need decay system as proof-of-concept
    class NeedDecaySystem:
        def update(self, world: WorldState, tick: int, event_bus: EventBus) -> None:
            for agent_id, agent in list(world.agents.items()):
                if not agent.biology.is_alive:
                    continue
                new_needs = agent.needs.decay_one_tick()
                new_agent = agent.with_needs(new_needs)
                # Age the agent
                new_bio = agent.biology.age_one_tick()
                new_agent = new_agent.with_biology(new_bio)
                world.agents[agent_id] = new_agent

    class StatusReporter:
        def update(self, world: WorldState, tick: int, event_bus: EventBus) -> None:
            pop = world.population_count()
            avg_food = 0
            avg_health = 0
            agents = world.get_alive_agents()
            if agents:
                avg_food = sum(a.needs.food for a in agents) / len(agents)
                avg_health = sum(a.biology.health for a in agents) / len(agents)

            if args.verbose or tick % 100 == 0:
                print(
                    f"  Tick {tick:>6d} | Pop: {pop:>4d} | "
                    f"Avg Food: {avg_food:.2f} | Avg Health: {avg_health:.2f}"
                )

            event_bus.emit(Event(
                tick=tick,
                event_type="status.report",
                data={"population": pop, "avg_food": avg_food, "avg_health": avg_health},
            ))

    try:
        engine.register_system("need_decay", 1, NeedDecaySystem())
        engine.register_system("status_reporter", 10, StatusReporter())
    except Exception as e:
        print(f"⚠️  Could not register systems: {e}")

    # Run simulation
    print(f"\n🚀 Starting simulation...\n")
    start_time = time.perf_counter()

    try:
        engine.run(ticks=args.ticks, target_tps=args.tps)
    except KeyboardInterrupt:
        print("\n\n⏸️  Simulation paused by user")

    elapsed = time.perf_counter() - start_time
    actual_tps = args.ticks / elapsed if elapsed > 0 else 0

    print(f"\n📊 Simulation Complete")
    print(f"   Ticks: {world.current_tick}")
    print(f"   Time: {elapsed:.1f}s ({actual_tps:.1f} ticks/sec)")

    stats = engine.get_stats()
    print(f"   Population: {stats['population']}")
    print(f"   Events logged: {stats['events_logged']}")
    print()


if __name__ == "__main__":
    main()
