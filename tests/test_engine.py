"""Tests for Simulation Engine — integration tests."""

import sys
sys.path.insert(0, "..")

import yaml
from engine.engine import SimulationEngine


def get_test_config():
    return {
        "world": {"width": 20, "height": 20, "seed": 42},
        "clock": {"ticks_per_day": 24, "max_ticks": 100},
        "agents": {
            "count": 5,
            "action_points_per_tick": 5,
            "perception_radius": 3,
            "starting_energy": 100,
            "starting_coins": 50,
        },
        "resources": {
            "types": [
                {"name": "food", "regen_rate": 0.05, "max_per_tile": 3},
                {"name": "wood", "regen_rate": 0.02, "max_per_tile": 2},
                {"name": "stone", "regen_rate": 0.01, "max_per_tile": 1},
            ]
        },
        "buildings": {
            "types": [
                {"name": "farm", "cost": {"wood": 5, "stone": 2}, "jobs": 3, "produces": "food"},
            ]
        },
        "learning": {
            "learning_rate": 0.1,
            "discount_factor": 0.95,
            "epsilon_start": 0.3,
            "epsilon_decay": 0.995,
            "epsilon_min": 0.01,
        },
        "economy": {"wage_base": 10},
    }


def test_engine_creation():
    config = get_test_config()
    engine = SimulationEngine(config)
    assert len(engine.agents) == 5
    assert engine.clock.tick == 0
    assert len(engine.learners) == 5


def test_engine_single_tick():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.tick()
    assert engine.clock.tick == 1
    for agent in engine.agents.values():
        assert agent.age == 1


def test_engine_100_ticks():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.run(max_ticks=100)
    assert engine.clock.tick == 100


def test_engine_agents_earn_rewards():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.run(max_ticks=50)
    total_rewards = sum(a.total_reward for a in engine.agents.values())
    assert total_rewards > 0


def test_engine_learners_update():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.run(max_ticks=50)
    for learner in engine.learners.values():
        assert learner.total_updates > 0
        assert learner.epsilon < 0.3  # should have decayed


def test_engine_state():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.run(max_ticks=10)
    state = engine.get_state()
    assert "clock" in state
    assert "agents" in state
    assert "world_stats" in state
    assert "learning" in state
    assert "avg_epsilon" in state["learning"]


def test_engine_tick_log():
    config = get_test_config()
    engine = SimulationEngine(config)
    engine.run(max_ticks=24)
    assert len(engine.tick_log) == 24
    assert engine.tick_log[0]["tick"] == 1
    assert "alive_agents" in engine.tick_log[0]


def test_engine_events_fire():
    config = get_test_config()
    config["clock"]["max_ticks"] = 500
    engine = SimulationEngine(config)
    engine.run(max_ticks=500)
    assert len(engine.events.event_history) > 0
