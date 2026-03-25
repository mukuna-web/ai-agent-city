"""Tests for Agent, Inventory, Personality, Actions."""

import sys
sys.path.insert(0, "..")

from agents.agent import Agent, Inventory, Personality, Action, ActionType, AgentState


def test_agent_creation():
    agent = Agent("TestBot", x=5, y=5)
    assert agent.name == "TestBot"
    assert agent.x == 5
    assert agent.y == 5
    assert agent.energy == 100.0
    assert agent.is_alive


def test_personality_random():
    import random
    rng = random.Random(42)
    p = Personality.random(rng)
    assert 0.0 <= p.curiosity <= 1.0
    assert 0.0 <= p.aggression <= 1.0
    assert 0.0 <= p.sociability <= 1.0
    assert 0.0 <= p.industriousness <= 1.0


def test_inventory_add_remove():
    inv = Inventory(capacity=10)
    added = inv.add("food", 5)
    assert added == 5
    assert inv.total == 5
    assert inv.has("food", 5)
    removed = inv.remove("food", 3)
    assert removed == 3
    assert inv.items["food"] == 2


def test_inventory_capacity():
    inv = Inventory(capacity=5)
    added = inv.add("food", 10)
    assert added == 5
    assert inv.is_full
    added2 = inv.add("wood", 1)
    assert added2 == 0


def test_inventory_remove_nonexistent():
    inv = Inventory()
    removed = inv.remove("gold", 5)
    assert removed == 0


def test_agent_execute_action():
    agent = Agent("Bot", x=0, y=0)
    agent.action_points = 5
    action = Action(ActionType.MOVE)  # cost 1
    assert agent.execute_action(action)
    assert agent.action_points == 4


def test_agent_not_enough_ap():
    agent = Agent("Bot", x=0, y=0)
    agent.action_points = 0
    action = Action(ActionType.GATHER)  # cost 2
    assert not agent.execute_action(action)


def test_agent_rest():
    agent = Agent("Bot", x=0, y=0)
    agent.energy = 50.0
    agent.rest()
    assert agent.energy == 75.0  # 50 + 25 recovery
    assert agent.state == AgentState.RESTING


def test_agent_rest_cap():
    agent = Agent("Bot", x=0, y=0)
    agent.energy = 90.0
    agent.rest()
    assert agent.energy == 100.0  # capped at max


def test_agent_skill_xp():
    agent = Agent("Bot", x=0, y=0)
    initial = agent.skills["foraging"]
    # Need enough XP to level up: threshold is 100 + level*50 = 150
    for _ in range(20):
        agent.gain_skill_xp("foraging", 10)
    assert agent.skills["foraging"] > initial


def test_agent_skill_check():
    agent = Agent("Bot", x=0, y=0, seed=42)
    agent.skills["foraging"] = 0.8
    successes = sum(1 for _ in range(100) if agent.skill_check("foraging", 0.5))
    assert successes > 50  # should succeed most of the time


def test_agent_trust():
    agent = Agent("Bot", x=0, y=0)
    agent.update_trust("other1", 0.1)
    assert agent.trust["other1"] == 0.6  # 0.5 + 0.1
    agent.update_trust("other1", -0.8)
    assert agent.trust["other1"] == 0.0  # clamped


def test_agent_reset_tick():
    agent = Agent("Bot", x=0, y=0)
    agent.action_points = 0
    agent.reset_tick()
    assert agent.action_points == 5
    assert agent.age == 1


def test_agent_summary():
    agent = Agent("Bot", x=3, y=7)
    summary = agent.summary()
    assert summary["name"] == "Bot"
    assert summary["position"] == (3, 7)
    assert "skills" in summary
    assert "energy" in summary


def test_agent_receive_reward():
    agent = Agent("Bot", x=0, y=0)
    agent.receive_reward(5.0)
    assert agent.last_reward == 5.0
    assert agent.total_reward == 5.0
    agent.receive_reward(3.0)
    assert agent.total_reward == 8.0
