"""Main simulation engine for AI Agent City."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from agents.agent import Action, ActionType, Agent, AgentState, Personality
from engine.clock import WorldClock
from engine.events import EventManager
from engine.world import Building, BuildingType, Resource, WorldGrid
from learning.learner import AgentLearner, SocialLearner, KnowledgeSharer
from learning.knowledge import SharedKnowledge
from learning.rewards import RewardShaper, snapshot_agent


AGENT_NAMES = [
    "Ada", "Bjorn", "Cleo", "Drake", "Eve", "Felix", "Gaia", "Hugo",
    "Iris", "Jax", "Kira", "Leo", "Maya", "Nero", "Ora", "Pike",
    "Quinn", "Rex", "Sage", "Tara", "Uma", "Vex", "Wren", "Xena",
    "Yuri", "Zara",
]


class SimulationEngine:
    def __init__(self, config: dict):
        self.config = config
        seed = config["world"]["seed"]
        self._rng = random.Random(seed)

        # Initialize world
        self.world = WorldGrid(
            width=config["world"]["width"],
            height=config["world"]["height"],
            seed=seed,
        )
        self.clock = WorldClock(ticks_per_day=config["clock"]["ticks_per_day"])
        self.events = EventManager(seed=seed)
        self.max_ticks = config["clock"]["max_ticks"]

        # Initialize agents
        self.agents: dict[str, Agent] = {}
        self._spawn_agents(config["agents"]["count"])

        # Initialize learning system
        self.learners: dict[str, AgentLearner] = {}
        self.social_learner = SocialLearner(seed=seed)
        self.knowledge_sharer = KnowledgeSharer(seed=seed)
        self.shared_knowledge = SharedKnowledge()
        self.reward_shaper = RewardShaper(
            gamma=config.get("learning", {}).get("discount_factor", 0.95),
        )
        self._init_learners(config.get("learning", {}))
        self._agent_snapshots: dict[str, dict] = {}  # pre-action state snapshots

        # Stats tracking
        self.tick_log: list[dict] = []
        self.running = False

    def _spawn_agents(self, count: int):
        for i in range(count):
            tile = self.world.find_random_passable_tile()
            name = AGENT_NAMES[i % len(AGENT_NAMES)]
            agent = Agent(
                name=name,
                x=tile.x,
                y=tile.y,
                personality=Personality.random(self._rng),
                seed=self._rng.randint(0, 999999),
            )
            agent.coins = self.config["agents"].get("starting_coins", 50)
            agent.energy = self.config["agents"].get("starting_energy", 100)
            agent.max_action_points = self.config["agents"].get("action_points_per_tick", 5)
            self.agents[agent.id] = agent
            tile.agent_ids.append(agent.id)

    def _init_learners(self, learning_config: dict):
        for agent_id, agent in self.agents.items():
            self.learners[agent_id] = AgentLearner(
                agent_id=agent_id,
                learning_rate=learning_config.get("learning_rate", 0.1),
                discount_factor=learning_config.get("discount_factor", 0.95),
                epsilon_start=learning_config.get("epsilon_start", 0.3),
                epsilon_decay=learning_config.get("epsilon_decay", 0.995),
                epsilon_min=learning_config.get("epsilon_min", 0.01),
                seed=agent._rng.randint(0, 999999),
            )

    def run(self, max_ticks: Optional[int] = None, callback=None):
        max_t = max_ticks or self.max_ticks
        self.running = True
        for _ in range(max_t):
            if not self.running:
                break
            self.tick()
            if callback:
                callback(self)

    def tick(self):
        # Phase 0: Reset agent action points
        for agent in self.agents.values():
            agent.reset_tick()

        # Phase 1: Perception
        self._phase_perceive()

        # Phase 1.5: Snapshot agent states for reward shaping
        for agent in self.agents.values():
            if agent.is_alive:
                self._agent_snapshots[agent.id] = snapshot_agent(agent)

        # Phase 2: Decision
        actions = self._phase_decide()

        # Phase 3: Resolution
        self._phase_resolve(actions)

        # Phase 4: Environment update
        self._phase_environment()

        # Phase 5: Learning (reward calculation)
        self._phase_learn()

        # Phase 6: Advance clock
        self.clock.advance()

        # Log tick
        self._log_tick()

    def _phase_perceive(self):
        radius = self.config["agents"].get("perception_radius", 3)
        for agent in self.agents.values():
            if not agent.is_alive:
                continue
            visible_tiles = self.world.get_tiles_in_radius(agent.x, agent.y, radius)
            nearby_agents = []
            for tile in visible_tiles:
                for aid in tile.agent_ids:
                    if aid != agent.id:
                        nearby_agents.append(aid)
            effects = self.events.get_effects_at(self.clock.tick, agent.x, agent.y)
            agent.perceive(visible_tiles, nearby_agents, effects)
            agent.perception["time_of_day"] = self.clock.time_of_day

    def _phase_decide(self) -> dict[str, Action]:
        actions = {}
        for agent in self.agents.values():
            if not agent.is_alive or not agent.can_act:
                actions[agent.id] = Action(ActionType.IDLE)
                continue
            learner = self.learners.get(agent.id)
            if learner:
                learner.memory.start_new_tick()
                actions[agent.id] = learner.choose_action(agent)
            else:
                actions[agent.id] = agent.decide()
        return actions

    def _phase_resolve(self, actions: dict[str, Action]):
        for agent_id, action in actions.items():
            agent = self.agents[agent_id]
            if not agent.is_alive:
                continue

            if action.type == ActionType.MOVE:
                self._resolve_move(agent, action)
            elif action.type == ActionType.GATHER:
                self._resolve_gather(agent, action)
            elif action.type == ActionType.REST:
                self._resolve_rest(agent, action)
            elif action.type == ActionType.TRADE:
                self._resolve_trade(agent, action)
            elif action.type == ActionType.WORK:
                self._resolve_work(agent, action)
            elif action.type == ActionType.COMMUNICATE:
                self._resolve_communicate(agent, action)
            elif action.type == ActionType.BUILD:
                self._resolve_build(agent, action)
            elif action.type == ActionType.LEARN:
                self._resolve_learn(agent, action)

    def _resolve_move(self, agent: Agent, action: Action):
        neighbors = self.world.get_passable_neighbors(agent.x, agent.y)
        if not neighbors:
            return
        if action.target and isinstance(action.target, tuple):
            tx, ty = action.target
            target_tile = self.world.get_tile(tx, ty)
            if target_tile and target_tile.is_passable:
                dest = target_tile
            else:
                dest = agent._rng.choice(neighbors)
        else:
            dest = agent._rng.choice(neighbors)

        if agent.execute_action(action):
            # Remove from old tile
            old_tile = self.world.get_tile(agent.x, agent.y)
            if old_tile and agent.id in old_tile.agent_ids:
                old_tile.agent_ids.remove(agent.id)
            # Move to new tile
            agent.x = dest.x
            agent.y = dest.y
            dest.agent_ids.append(agent.id)
            agent.state = AgentState.EXPLORING

    def _resolve_gather(self, agent: Agent, action: Action):
        tile = self.world.get_tile(agent.x, agent.y)
        if not tile or not tile.resources:
            return
        if agent.inventory.is_full:
            return
        if agent.execute_action(action):
            for resource in tile.resources:
                if resource.quantity > 0:
                    taken = resource.take(1)
                    if taken > 0:
                        agent.inventory.add(resource.name, taken)
                        agent.gain_skill_xp("foraging", 10)
                        agent.state = AgentState.GATHERING
                        agent.receive_reward(1.0)
                    break

    def _resolve_rest(self, agent: Agent, action: Action):
        if agent.execute_action(action):
            agent.rest()
            if agent.energy < 50:
                agent.receive_reward(2.0)  # strong reward for resting when low
            else:
                agent.receive_reward(0.5)

    def _resolve_trade(self, agent: Agent, action: Action):
        tile = self.world.get_tile(agent.x, agent.y)
        if not tile:
            return
        other_ids = [aid for aid in tile.agent_ids if aid != agent.id]
        if not other_ids:
            return
        other = self.agents.get(agent._rng.choice(other_ids))
        if not other or not other.is_alive:
            return
        if agent.execute_action(action):
            # Simple barter: exchange random items
            agent_items = list(agent.inventory.items.keys())
            other_items = list(other.inventory.items.keys())
            if agent_items and other_items:
                give = agent._rng.choice(agent_items)
                receive = other._rng.choice(other_items)
                if agent.inventory.remove(give, 1) and other.inventory.remove(receive, 1):
                    agent.inventory.add(receive, 1)
                    other.inventory.add(give, 1)
                    agent.receive_reward(2.0)
                    other.receive_reward(2.0)
                    agent.gain_skill_xp("trading", 15)
                    other.gain_skill_xp("trading", 15)
                    agent.update_trust(other.id, 0.05)
                    other.update_trust(agent.id, 0.05)
                    agent.state = AgentState.TRADING
                    other.state = AgentState.TRADING

    def _resolve_work(self, agent: Agent, action: Action):
        tile = self.world.get_tile(agent.x, agent.y)
        if not tile or not tile.building or not tile.building.has_vacancy:
            return
        if agent.execute_action(action):
            wage = self.config["economy"].get("wage_base", 10)
            agent.coins += wage
            agent.state = AgentState.WORKING
            agent.gain_skill_xp("crafting", 10)
            agent.receive_reward(1.5)

    def _resolve_communicate(self, agent: Agent, action: Action):
        tile = self.world.get_tile(agent.x, agent.y)
        if not tile:
            return
        other_ids = [aid for aid in tile.agent_ids if aid != agent.id]
        if not other_ids:
            return
        other = self.agents.get(agent._rng.choice(other_ids))
        if not other:
            return
        if agent.execute_action(action):
            agent.gain_skill_xp("socializing", 10)
            other.gain_skill_xp("socializing", 5)
            agent.update_trust(other.id, 0.03)
            other.update_trust(agent.id, 0.03)
            agent.mood = min(1.0, agent.mood + 0.05 * agent.personality.sociability)
            agent.state = AgentState.COMMUNICATING
            agent.receive_reward(0.5)

    def _resolve_build(self, agent: Agent, action: Action):
        if not agent.skill_check("building", 0.7):
            return
        if agent.execute_action(action):
            agent.gain_skill_xp("building", 20)
            agent.receive_reward(3.0)
            agent.state = AgentState.WORKING

    def _resolve_learn(self, agent: Agent, action: Action):
        tile = self.world.get_tile(agent.x, agent.y)
        if tile and tile.building and tile.building.type.name == "library":
            xp_bonus = 25
        else:
            xp_bonus = 10
        if agent.execute_action(action):
            skill = agent._rng.choice(list(agent.skills.keys()))
            agent.gain_skill_xp(skill, xp_bonus)
            agent.state = AgentState.LEARNING
            agent.receive_reward(1.0)

    def _phase_environment(self):
        # Resource regeneration on new day
        if self.clock.is_new_day() and self.clock.tick > 0:
            self.world.regenerate_resources(self.config["resources"]["types"])

        # Random events
        self.events.check_random_events(
            self.clock.tick, self.world.width, self.world.height
        )

    def _phase_learn(self):
        # Penalty for idle agents
        for agent in self.agents.values():
            if agent.last_action and agent.last_action.type == ActionType.IDLE:
                agent.receive_reward(-1.0)

        # Update Q-values with shaped rewards
        for agent in self.agents.values():
            learner = self.learners.get(agent.id)
            if not learner:
                continue

            base_reward = agent.last_reward
            snap = self._agent_snapshots.get(agent.id)

            if snap:
                # Add context bonus based on action appropriateness
                action_name = agent.last_action.type.value if agent.last_action else "idle"
                context_bonus = self.reward_shaper.compute_context_bonus(agent, action_name)
                # Apply potential-based shaping
                shaped_reward = self.reward_shaper.shape(snap, agent, base_reward + context_bonus)
            else:
                shaped_reward = base_reward

            learner.update(agent, shaped_reward)

        # Social learning every 10 ticks
        if self.clock.tick % 10 == 0:
            for agent in self.agents.values():
                learner = self.learners.get(agent.id)
                if not learner:
                    continue
                tile = self.world.get_tile(agent.x, agent.y)
                if not tile:
                    continue
                neighbor_ids = [aid for aid in tile.agent_ids if aid != agent.id]
                if not neighbor_ids:
                    continue
                neighbors = {aid: self.agents[aid] for aid in neighbor_ids if aid in self.agents}
                neighbor_learners = {aid: self.learners[aid] for aid in neighbor_ids if aid in self.learners}
                self.social_learner.observe_and_learn(agent, learner, neighbors, neighbor_learners)

    def _log_tick(self):
        alive = sum(1 for a in self.agents.values() if a.is_alive)
        avg_energy = sum(a.energy for a in self.agents.values()) / max(len(self.agents), 1)
        avg_reward = sum(a.total_reward for a in self.agents.values()) / max(len(self.agents), 1)
        total_coins = sum(a.coins for a in self.agents.values())
        self.tick_log.append({
            "tick": self.clock.tick,
            "day": self.clock.day,
            "hour": self.clock.hour,
            "alive_agents": alive,
            "avg_energy": round(avg_energy, 1),
            "avg_reward": round(avg_reward, 1),
            "total_coins": total_coins,
            "active_events": len(self.events.active_events),
            "world_resources": self.world.stats()["total_resources"],
        })

    def get_state(self) -> dict:
        learning_stats = {}
        for aid, learner in self.learners.items():
            learning_stats[aid] = learner.get_stats()
        avg_epsilon = sum(l.epsilon for l in self.learners.values()) / max(len(self.learners), 1)
        avg_q_size = sum(len(l.q_table) for l in self.learners.values()) / max(len(self.learners), 1)

        return {
            "clock": str(self.clock),
            "tick": self.clock.tick,
            "agents": {aid: a.summary() for aid, a in self.agents.items()},
            "world_stats": self.world.stats(),
            "active_events": [
                {"name": e.name, "type": e.type, "effects": e.effects}
                for e in self.events.get_active_events(self.clock.tick)
            ],
            "learning": {
                "avg_epsilon": round(avg_epsilon, 4),
                "avg_q_table_size": round(avg_q_size, 1),
                "per_agent": learning_stats,
            },
        }

    def save_snapshot(self, path: str):
        with open(path, "w") as f:
            json.dump(self.get_state(), f, indent=2)
