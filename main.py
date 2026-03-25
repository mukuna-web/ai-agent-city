"""AI Agent City — Main entry point."""

import json
import sys
from pathlib import Path

import yaml

from engine.engine import SimulationEngine


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def print_tick_summary(engine: SimulationEngine):
    if engine.clock.tick % 24 == 0 and engine.clock.tick > 0:
        state = engine.get_state()
        day = engine.clock.day
        alive = sum(1 for a in engine.agents.values() if a.is_alive)
        avg_reward = sum(a.total_reward for a in engine.agents.values()) / max(len(engine.agents), 1)
        resources = state["world_stats"]["total_resources"]
        events = len(state["active_events"])
        print(f"  Day {day}: {alive} agents alive | avg reward: {avg_reward:.1f} | resources: {resources} | events: {events}")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)

    print("=" * 60)
    print("  AI AGENT CITY — Simulation")
    print("=" * 60)
    print(f"  World: {config['world']['width']}x{config['world']['height']}")
    print(f"  Agents: {config['agents']['count']}")
    print(f"  Max ticks: {config['clock']['max_ticks']}")
    print(f"  Seed: {config['world']['seed']}")
    print("=" * 60)

    engine = SimulationEngine(config)

    world_stats = engine.world.stats()
    print(f"\n  World generated:")
    print(f"    Terrain: {world_stats['terrain']}")
    print(f"    Resources: {world_stats['total_resources']}")
    print(f"    Agents spawned: {len(engine.agents)}")
    print()

    # Print initial agent roster
    print("  Agent Roster:")
    for agent in list(engine.agents.values())[:10]:
        print(f"    {agent.name} @ ({agent.x},{agent.y}) — personality: "
              f"cur={agent.personality.curiosity:.1f} "
              f"soc={agent.personality.sociability:.1f} "
              f"ind={agent.personality.industriousness:.1f}")
    if len(engine.agents) > 10:
        print(f"    ... and {len(engine.agents) - 10} more")
    print()

    print("  Running simulation...")
    engine.run(callback=print_tick_summary)

    # Final summary
    print()
    print("=" * 60)
    print("  SIMULATION COMPLETE")
    print("=" * 60)
    state = engine.get_state()
    alive = sum(1 for a in engine.agents.values() if a.is_alive)
    print(f"  Ticks: {engine.clock.tick}")
    print(f"  Days: {engine.clock.day}")
    print(f"  Agents alive: {alive}/{len(engine.agents)}")
    print()

    # Top agents by reward
    sorted_agents = sorted(engine.agents.values(), key=lambda a: a.total_reward, reverse=True)
    print("  Top 5 Agents by Total Reward:")
    for i, agent in enumerate(sorted_agents[:5]):
        print(f"    {i+1}. {agent.name} — reward: {agent.total_reward:.1f}, "
              f"coins: {agent.coins}, skills: {', '.join(f'{k}={v:.2f}' for k, v in agent.skills.items())}")

    # Skill leaders
    print()
    print("  Skill Leaders:")
    for skill in ["foraging", "crafting", "trading", "building", "socializing"]:
        leader = max(engine.agents.values(), key=lambda a: a.skills.get(skill, 0))
        print(f"    {skill}: {leader.name} ({leader.skills[skill]:.2f})")

    # Save snapshot
    snapshot_path = "simulation_result.json"
    engine.save_snapshot(snapshot_path)
    print(f"\n  Snapshot saved to {snapshot_path}")

    # Save tick log
    log_path = "tick_log.json"
    with open(log_path, "w") as f:
        json.dump(engine.tick_log, f, indent=2)
    print(f"  Tick log saved to {log_path}")


if __name__ == "__main__":
    main()
