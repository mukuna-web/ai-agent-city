"""Tests for Learning System — AgentLearner, Memory, Skills."""

import sys
sys.path.insert(0, "..")

from agents.agent import Agent, ActionType
from learning.learner import AgentLearner, discretize_state, SocialLearner
from learning.memory import AgentMemory, MemoryEntry, WorkingMemory, ShortTermMemory, LongTermMemory
from learning.skills import SkillSystem
from learning.replay import ReplayBuffer, PrioritizedReplayBuffer
from learning.rewards import RewardShaper, snapshot_agent


# --- Memory Tests ---

def test_working_memory():
    wm = WorkingMemory(capacity=3)
    for i in range(5):
        wm.add(MemoryEntry(tick=i, event_type="test", data={"i": i}, importance=i * 0.2))
    assert len(wm) == 3
    wm.clear()
    assert len(wm) == 0


def test_short_term_memory():
    stm = ShortTermMemory(capacity=50, tick_window=10)
    for i in range(20):
        stm.add(MemoryEntry(tick=i, event_type="action", data={"i": i}))
    recalled = stm.recall(current_tick=19, event_type="action")
    assert all(e.tick >= 9 for e in recalled)


def test_long_term_memory():
    ltm = LongTermMemory()
    # Low importance — not stored
    ltm.store(MemoryEntry(tick=1, event_type="test", data={}, importance=0.3))
    assert len(ltm) == 0
    # High importance — stored
    ltm.store(MemoryEntry(tick=2, event_type="test", data={}, importance=0.8))
    assert len(ltm) == 1


def test_long_term_facts():
    ltm = LongTermMemory()
    ltm.store_fact("resource:food", (10, 20))
    assert ltm.recall_fact("resource:food") == (10, 20)
    assert ltm.recall_fact("nonexistent") is None


def test_agent_memory_integration():
    mem = AgentMemory()
    mem.record(tick=1, event_type="action", data={"a": 1}, importance=0.9)
    mem.record(tick=2, event_type="obs", data={"b": 2}, importance=0.3)
    context = mem.get_decision_context(current_tick=2)
    assert "working" in context
    assert "recent" in context
    assert "important" in context


def test_memory_location_recall():
    mem = AgentMemory()
    mem.remember_location("market", 15, 20)
    loc = mem.recall_location("market")
    assert loc == (15, 20)


# --- Learner Tests ---

def test_discretize_state():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    state = discretize_state(agent)
    assert isinstance(state, tuple)
    assert len(state) == 6


def test_learner_choose_action():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    learner = AgentLearner("test-id", seed=42)
    action = learner.choose_action(agent)
    assert action.type in ActionType


def test_learner_update():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    learner = AgentLearner("test-id", seed=42)
    learner.choose_action(agent)
    initial_epsilon = learner.epsilon
    learner.update(agent, reward=1.0)
    assert learner.epsilon < initial_epsilon
    assert learner.total_updates == 1
    assert len(learner.q_table) > 0


def test_learner_epsilon_decay():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "afternoon"}
    learner = AgentLearner("test-id", epsilon_start=0.5, epsilon_decay=0.9, seed=42)
    for _ in range(10):
        learner.choose_action(agent)
        learner.update(agent, reward=1.0)
    assert learner.epsilon < 0.5


def test_learner_stats():
    learner = AgentLearner("test-id")
    stats = learner.get_stats()
    assert "q_table_size" in stats
    assert "epsilon" in stats
    assert "memory_size" in stats


# --- Skill System Tests ---

def test_skill_creation():
    skills = SkillSystem(seed=42)
    assert len(skills.skills) == 5
    assert "foraging" in skills.skills
    assert skills.get_proficiency("foraging") == 0.1


def test_skill_practice():
    skills = SkillSystem(seed=42)
    # Practice many times to level up
    for _ in range(30):
        skills.practice("foraging", difficulty=0.3, xp_amount=15)
    assert skills.get_proficiency("foraging") > 0.1


def test_skill_check():
    skills = SkillSystem(seed=42)
    skills.skills["trading"].proficiency = 0.9
    successes = sum(1 for _ in range(100) if skills.check("trading", 0.5))
    assert successes > 50


def test_skill_specialization():
    skills = SkillSystem(seed=42)
    for _ in range(20):
        skills.practice("crafting", 0.3)
    assert skills.get_specialization() == "crafting"


def test_skill_summary():
    skills = SkillSystem()
    summary = skills.get_summary()
    assert "foraging" in summary
    assert "proficiency" in summary["foraging"]
    assert "level" in summary["foraging"]


def test_best_skill():
    skills = SkillSystem()
    skills.skills["building"].proficiency = 0.8
    name, prof = skills.get_best_skill()
    assert name == "building"
    assert prof == 0.8


# --- Social Learning Tests ---

def test_social_learner():
    observer = Agent("Observer", 0, 0)
    observer.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    neighbor = Agent("Neighbor", 0, 0)
    neighbor.total_reward = 100.0
    observer.trust[neighbor.id] = 0.8

    obs_learner = AgentLearner(observer.id, seed=1)
    nb_learner = AgentLearner(neighbor.id, seed=2)
    # Give neighbor some Q-values
    nb_learner.q_table[("high", "some", False, "morning", "mid", True)] = {"gather": 5.0}

    sl = SocialLearner(seed=42)
    sl.observe_and_learn(
        observer, obs_learner,
        {neighbor.id: neighbor},
        {neighbor.id: nb_learner},
    )
    # Observer should have picked up some Q-values
    assert len(obs_learner.q_table) > 0 or len(obs_learner.memory.short_term) > 0


# --- Replay Buffer Tests ---

def test_replay_buffer_push_and_sample():
    buf = ReplayBuffer(capacity=50, seed=42)
    for i in range(20):
        buf.push(("s", i), "move", float(i), ("s", i + 1), tick=i)
    assert len(buf) == 20
    batch = buf.sample(5)
    assert len(batch) == 5


def test_replay_buffer_capacity():
    buf = ReplayBuffer(capacity=10, seed=42)
    for i in range(25):
        buf.push(("s",), "act", 1.0, ("s2",), tick=i)
    assert len(buf) == 10


def test_replay_buffer_sample_larger_than_size():
    buf = ReplayBuffer(capacity=100, seed=42)
    for i in range(3):
        buf.push(("s",), "act", 1.0, ("s2",), tick=i)
    batch = buf.sample(10)
    assert len(batch) == 3


def test_prioritized_replay_prefers_high_reward():
    buf = PrioritizedReplayBuffer(capacity=100, alpha=1.0, seed=42)
    # Add 1 high-reward and 99 low-reward transitions
    buf.push(("high",), "act", 10.0, ("next",), tick=0)
    for i in range(99):
        buf.push(("low", i), "act", 0.01, ("next",), tick=i + 1)
    # Sample many batches and count how often "high" state appears
    high_count = 0
    for _ in range(100):
        batch = buf.sample(10)
        for t in batch:
            if t.state == ("high",):
                high_count += 1
    # High-reward transition should appear much more than 10% of samples
    assert high_count > 50


def test_learner_replay_integration():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    learner = AgentLearner("test-id", replay_every=1, replay_batch_size=2, seed=42)
    # Run enough updates to trigger replay
    for _ in range(10):
        learner.choose_action(agent)
        learner.update(agent, reward=1.0)
    assert learner.replay_updates > 0
    assert len(learner.replay_buffer) == 10
    stats = learner.get_stats()
    assert "replay_updates" in stats
    assert "replay_buffer_size" in stats


# --- Reward Shaping Tests ---

def test_reward_shaper_potential():
    shaper = RewardShaper()
    agent = Agent("Test", 0, 0)
    agent.energy = 80.0
    agent.coins = 100
    agent.mood = 0.7
    p = shaper.potential(agent)
    assert p > 0  # healthy agent should have positive potential


def test_reward_shaper_low_energy_penalty():
    shaper = RewardShaper()
    healthy = Agent("Healthy", 0, 0)
    healthy.energy = 80.0
    dying = Agent("Dying", 0, 0)
    dying.energy = 5.0
    assert shaper.potential(healthy) > shaper.potential(dying)


def test_reward_shaper_shape():
    shaper = RewardShaper(gamma=0.95)
    agent = Agent("Test", 0, 0)
    agent.energy = 50.0
    agent.coins = 50
    snap = snapshot_agent(agent)
    # Agent improves
    agent.energy = 70.0
    agent.coins = 60
    shaped = shaper.shape(snap, agent, base_reward=1.0)
    # Shaped reward should be > base because agent improved
    assert shaped > 1.0


def test_reward_shaper_shape_decline():
    shaper = RewardShaper(gamma=0.95)
    agent = Agent("Test", 0, 0)
    agent.energy = 80.0
    agent.coins = 100
    snap = snapshot_agent(agent)
    # Agent declines
    agent.energy = 30.0
    agent.coins = 20
    shaped = shaper.shape(snap, agent, base_reward=1.0)
    # Shaped reward should be < base because agent declined
    assert shaped < 1.0


def test_snapshot_agent():
    agent = Agent("Test", 0, 0)
    agent.energy = 75.0
    agent.coins = 42
    agent.inventory.add("food", 3)
    snap = snapshot_agent(agent)
    assert snap["energy"] == 75.0
    assert snap["coins"] == 42
    assert snap["inventory_total"] == 3


def test_context_bonus_rest_when_tired():
    shaper = RewardShaper()
    agent = Agent("Test", 0, 0)
    agent.energy = 10.0
    bonus = shaper.compute_context_bonus(agent, "rest")
    assert bonus > 0


def test_context_bonus_work_when_tired_penalized():
    shaper = RewardShaper()
    agent = Agent("Test", 0, 0)
    agent.energy = 10.0
    bonus = shaper.compute_context_bonus(agent, "work")
    assert bonus < 0


def test_learner_lr_decay():
    agent = Agent("Test", 0, 0)
    agent.perception = {"nearby_agents": [], "tiles": [], "time_of_day": "morning"}
    learner = AgentLearner("test-id", learning_rate=0.1, seed=42)
    initial_lr = learner.learning_rate
    for _ in range(100):
        learner.choose_action(agent)
        learner.update(agent, reward=1.0)
    assert learner.learning_rate < initial_lr
