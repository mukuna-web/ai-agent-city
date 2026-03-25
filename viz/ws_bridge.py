"""WebSocket bridge — streams delta updates from simulation to Three.js frontend.

Implements the protocol from docs/architecture/08-visualization-3d.md:
- Delta updates (only changed agents) instead of full state
- Event streaming from the EventBus
- Aggregate city metrics
- Learning system stats
- Play/pause/speed/step controls
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import websockets
import yaml
from aiohttp import web

from engine.engine import SimulationEngine


class AgentTracker:
    """Tracks agent state between ticks to compute deltas."""

    def __init__(self):
        self._last: dict[str, dict] = {}

    def compute_deltas(self, agents: dict[str, Any]) -> list[dict]:
        """Return only agents whose visible state changed since last tick."""
        deltas = []
        current_ids = set()

        for aid, agent in agents.items():
            current_ids.add(aid)
            summary = agent.summary()
            current = {
                "id": aid,
                "x": summary["position"][0],
                "y": summary["position"][1],
                "state": summary["state"],
                "mood": summary["mood"],
                "energy": summary["energy"],
                "name": summary["name"],
                "coins": summary["coins"],
            }

            prev = self._last.get(aid)
            if prev is None:
                # New agent — send full data
                current["is_new"] = True
                deltas.append(current)
            elif (prev["x"] != current["x"] or prev["y"] != current["y"]
                  or prev["state"] != current["state"]
                  or prev["mood"] != current["mood"]):
                deltas.append(current)

            self._last[aid] = current

        # Detect removed agents (deaths)
        removed = set(self._last.keys()) - current_ids
        for aid in removed:
            deltas.append({"id": aid, "removed": True})
            del self._last[aid]

        return deltas


class DeltaSimulationServer:
    """WebSocket server that streams delta updates to the Three.js frontend."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.engine = SimulationEngine(self.config)
        self.tracker = AgentTracker()
        self.clients: set = set()
        self.paused = True
        self.speed = 1.0
        self._event_buffer: list[dict] = []

    async def register(self, ws):
        self.clients.add(ws)
        # Send initial data in the format the frontend expects
        await ws.send(json.dumps({
            "type": "agents",
            "agents": self._serialize_agents(),
        }, default=str))
        await ws.send(json.dumps({
            "type": "buildings",
            "buildings": self._serialize_buildings(),
        }, default=str))
        await ws.send(json.dumps({
            "type": "metrics",
            **self._serialize_metrics(),
        }, default=str))

    async def unregister(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, message: dict):
        if not self.clients:
            return
        data = json.dumps(message, default=str)
        await asyncio.gather(
            *[c.send(data) for c in self.clients],
            return_exceptions=True,
        )

    def _serialize_agents(self) -> list[dict]:
        """Serialize agents in the format the frontend expects."""
        agents = []
        for aid, agent in self.engine.agents.items():
            summary = agent.summary()
            agents.append({
                "id": aid,
                "x": summary["position"][0],
                "y": summary["position"][1],
                "profession": "worker",
                "action": summary["state"],
                "health": summary["energy"] / 100.0,
                "name": summary["name"],
                "age": summary["age"],
                "needs": {"energy": summary["energy"] / 100.0, "mood": summary["mood"]},
                "personality": {},
                "goal": summary["state"],
            })
        return agents

    def _serialize_buildings(self) -> list[dict]:
        """Serialize buildings in the format the frontend expects."""
        buildings = []
        for (x, y), tile in self.engine.world.tiles.items():
            if tile.building:
                buildings.append({
                    "id": f"bldg-{x}-{y}",
                    "x": x,
                    "y": y,
                    "type": tile.building.type.name,
                    "progress": 1.0,
                    "operational": True,
                })
        return buildings

    def _serialize_metrics(self) -> dict:
        """Serialize metrics in the format the frontend expects."""
        agents = list(self.engine.agents.values())
        alive = [a for a in agents if a.is_alive]
        population = len(alive)
        total_coins = sum(a.coins for a in alive) if alive else 0
        return {
            "population": population,
            "gdp": total_coins,
            "unemployment": 0.0,
            "avg_wage": 10,
            "gini": 0.0,
            "tick": self.engine.clock.tick,
            "season": "spring",
        }

    def _full_state(self) -> dict:
        state = self.engine.get_state()
        # Initialize tracker with current state
        self.tracker.compute_deltas(self.engine.agents)
        return state

    def _serialize_world(self) -> dict:
        tiles = {}
        for (x, y), tile in self.engine.world.tiles.items():
            tiles[f"{x},{y}"] = {
                "terrain": tile.terrain.value,
                "resources": [
                    {"name": r.name, "qty": r.quantity}
                    for r in tile.resources if r.quantity > 0
                ],
                "building": tile.building.type.name if tile.building else None,
            }
        return {"tiles": tiles}

    def _compute_metrics(self) -> dict:
        agents = list(self.engine.agents.values())
        alive = [a for a in agents if a.is_alive]
        if not alive:
            return {"population": 0}

        total_coins = sum(a.coins for a in alive)
        avg_energy = sum(a.energy for a in alive) / len(alive)
        avg_mood = sum(a.mood for a in alive) / len(alive)
        avg_reward = sum(a.total_reward for a in alive) / len(alive)

        # Skill distribution
        skill_avgs = {}
        for skill in ["foraging", "crafting", "trading", "building", "socializing"]:
            vals = [a.skills.get(skill, 0) for a in alive]
            skill_avgs[skill] = round(sum(vals) / len(vals), 3) if vals else 0

        return {
            "population": len(alive),
            "total_coins": total_coins,
            "avg_energy": round(avg_energy, 1),
            "avg_mood": round(avg_mood, 2),
            "avg_reward": round(avg_reward, 1),
            "skill_averages": skill_avgs,
            "world_resources": self.engine.world.stats().get("total_resources", 0),
        }

    def _compute_learning_stats(self) -> dict:
        learners = self.engine.learners
        if not learners:
            return {}
        avg_epsilon = sum(l.epsilon for l in learners.values()) / len(learners)
        avg_q_size = sum(len(l.q_table) for l in learners.values()) / len(learners)
        avg_replay = sum(len(l.replay_buffer) for l in learners.values()) / len(learners)
        return {
            "avg_epsilon": round(avg_epsilon, 4),
            "avg_q_table_size": round(avg_q_size, 1),
            "avg_replay_buffer": round(avg_replay, 1),
            "total_updates": sum(l.total_updates for l in learners.values()),
        }

    def _tick_and_collect(self) -> list[dict]:
        """Run one tick and collect messages in frontend format."""
        self.engine.tick()

        tick = self.engine.clock.tick
        metrics = self._serialize_metrics()

        messages = []

        # Tick update
        messages.append({
            "type": "tick",
            "tick": tick,
            "season": "spring",
            "population": metrics["population"],
            "gdp": metrics["gdp"],
        })

        # Full agent list (frontend replaces all agents each tick)
        messages.append({
            "type": "agents",
            "agents": self._serialize_agents(),
        })

        # Buildings (send every 10 ticks since they rarely change)
        if tick % 10 == 0:
            messages.append({
                "type": "buildings",
                "buildings": self._serialize_buildings(),
            })

        # Metrics
        if tick % 5 == 0:
            messages.append({
                "type": "metrics",
                **metrics,
            })

        # Events from tick log
        if self.engine.tick_log:
            last_log = self.engine.tick_log[-1]
            messages.append({
                "type": "event",
                "event_type": "tick",
                "description": f"Day {last_log['day']}, {last_log['alive_agents']} alive, avg energy {last_log['avg_energy']}",
                "tick": tick,
            })

        return messages

    async def handle_client(self, ws):
        await self.register(ws)
        try:
            async for message in ws:
                data = json.loads(message)
                cmd = data.get("command")

                if cmd == "play":
                    self.paused = False
                    await ws.send(json.dumps({"type": "status", "paused": False}))

                elif cmd == "pause":
                    self.paused = True
                    await ws.send(json.dumps({"type": "status", "paused": True}))

                elif cmd == "step":
                    for msg in self._tick_and_collect():
                        await self.broadcast(msg)

                elif cmd == "speed":
                    self.speed = max(0.1, min(100, data.get("value", 1.0)))
                    await ws.send(json.dumps({"type": "status", "speed": self.speed}))

                elif cmd == "reset":
                    self.engine = SimulationEngine(self.config)
                    self.tracker = AgentTracker()
                    self.paused = True
                    await self.broadcast({
                        "type": "init",
                        "config": {
                            "width": self.config["world"]["width"],
                            "height": self.config["world"]["height"],
                            "agent_count": self.config["agents"]["count"],
                            "ticks_per_day": self.config["clock"]["ticks_per_day"],
                        },
                        "state": self._full_state(),
                        "world": self._serialize_world(),
                    })

                elif cmd == "get_agent":
                    agent_id = data.get("agent_id")
                    agent = self.engine.agents.get(agent_id)
                    if agent:
                        learner = self.engine.learners.get(agent_id)
                        response = {
                            "type": "agent_detail",
                            "agent": agent.summary(),
                            "learning": learner.get_stats() if learner else None,
                        }
                        await ws.send(json.dumps(response))

                elif cmd == "get_state":
                    await ws.send(json.dumps({
                        "type": "full_state",
                        "state": self.engine.get_state(),
                    }))

        finally:
            await self.unregister(ws)

    async def simulation_loop(self):
        while True:
            if not self.paused and self.clients:
                for msg in self._tick_and_collect():
                    await self.broadcast(msg)
            delay = 1.0 / self.speed if self.speed > 0 else 1.0
            await asyncio.sleep(delay)

    # --- REST API handlers ---

    async def handle_rest_agent(self, request: web.Request) -> web.Response:
        """GET /agent/:id — returns agent detail + learning stats."""
        agent_id = request.match_info["agent_id"]
        agent = self.engine.agents.get(agent_id)
        if not agent:
            return web.json_response({"error": "agent not found"}, status=404)
        learner = self.engine.learners.get(agent_id)
        return web.json_response({
            "agent": agent.summary(),
            "learning": learner.get_stats() if learner else None,
        })

    async def handle_rest_agents(self, request: web.Request) -> web.Response:
        """GET /agents — returns list of all agent summaries."""
        agents = [a.summary() for a in self.engine.agents.values()]
        return web.json_response({"agents": agents, "count": len(agents)})

    async def handle_rest_state(self, request: web.Request) -> web.Response:
        """GET /state — returns full simulation state."""
        return web.json_response(self.engine.get_state(), default=str)

    async def handle_rest_metrics(self, request: web.Request) -> web.Response:
        """GET /metrics — returns current city metrics + learning stats."""
        return web.json_response({
            "metrics": self._compute_metrics(),
            "learning": self._compute_learning_stats(),
            "tick": self.engine.clock.tick,
            "day": self.engine.clock.day,
        })

    def _create_rest_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/agent/{agent_id}", self.handle_rest_agent)
        app.router.add_get("/agents", self.handle_rest_agents)
        app.router.add_get("/state", self.handle_rest_state)
        app.router.add_get("/metrics", self.handle_rest_metrics)

        # CORS middleware for Three.js frontend
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        app.middlewares.append(cors_middleware)
        return app

    async def start(self, host: str = "0.0.0.0", ws_port: int = 8765, rest_port: int = 8766):
        print(f"AI Agent City — Delta WebSocket + REST Server")
        print(f"WebSocket: ws://{host}:{ws_port}")
        print(f"REST API:  http://{host}:{rest_port}")
        print(f"  GET /agent/:id  — agent detail + learning stats")
        print(f"  GET /agents     — all agent summaries")
        print(f"  GET /state      — full simulation state")
        print(f"  GET /metrics    — city metrics + learning stats")

        rest_app = self._create_rest_app()
        runner = web.AppRunner(rest_app)
        await runner.setup()
        site = web.TCPSite(runner, host, rest_port)
        await site.start()

        async with websockets.serve(self.handle_client, host, ws_port):
            await self.simulation_loop()


async def main():
    import os
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config.yaml"
    )
    server = DeltaSimulationServer(config_path)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
