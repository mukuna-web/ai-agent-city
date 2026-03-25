"""WebSocket server that streams simulation data to the browser dashboard."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import websockets
import yaml

from engine.engine import SimulationEngine


class SimulationServer:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.engine = SimulationEngine(self.config)
        self.clients: set = set()
        self.running = False
        self.speed = 1.0  # ticks per second
        self.paused = True

    async def register(self, ws):
        self.clients.add(ws)
        # Send initial state
        await ws.send(json.dumps({
            "type": "init",
            "config": {
                "width": self.config["world"]["width"],
                "height": self.config["world"]["height"],
                "agent_count": self.config["agents"]["count"],
            },
            "state": self.engine.get_state(),
            "world": self._serialize_world(),
        }))

    async def unregister(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, message: dict):
        if self.clients:
            data = json.dumps(message)
            await asyncio.gather(
                *[client.send(data) for client in self.clients],
                return_exceptions=True,
            )

    def _serialize_world(self) -> dict:
        tiles = {}
        for (x, y), tile in self.engine.world.tiles.items():
            tiles[f"{x},{y}"] = {
                "terrain": tile.terrain.value,
                "resources": [{"name": r.name, "qty": r.quantity} for r in tile.resources if r.quantity > 0],
                "building": tile.building.type.name if tile.building else None,
                "agents": tile.agent_ids,
            }
        return {"tiles": tiles}

    async def handle_client(self, ws):
        await self.register(ws)
        try:
            async for message in ws:
                data = json.loads(message)
                cmd = data.get("command")
                if cmd == "play":
                    self.paused = False
                elif cmd == "pause":
                    self.paused = True
                elif cmd == "step":
                    self.engine.tick()
                    await self.broadcast({
                        "type": "tick",
                        "state": self.engine.get_state(),
                        "world": self._serialize_world(),
                    })
                elif cmd == "speed":
                    self.speed = max(0.1, min(100, data.get("value", 1.0)))
                elif cmd == "reset":
                    self.engine = SimulationEngine(self.config)
                    self.paused = True
                    await self.broadcast({
                        "type": "init",
                        "config": {
                            "width": self.config["world"]["width"],
                            "height": self.config["world"]["height"],
                            "agent_count": self.config["agents"]["count"],
                        },
                        "state": self.engine.get_state(),
                        "world": self._serialize_world(),
                    })
        finally:
            await self.unregister(ws)

    async def simulation_loop(self):
        while True:
            if not self.paused and self.clients:
                self.engine.tick()
                await self.broadcast({
                    "type": "tick",
                    "state": self.engine.get_state(),
                    "world": self._serialize_world(),
                })
            delay = 1.0 / self.speed if self.speed > 0 else 1.0
            await asyncio.sleep(delay)

    async def start(self, host: str = "localhost", port: int = 8765):
        print(f"Starting AI Agent City server on ws://{host}:{port}")
        print(f"Open viz/index.html in your browser to view the dashboard")

        async with websockets.serve(self.handle_client, host, port):
            await self.simulation_loop()


async def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config.yaml"
    )
    server = SimulationServer(config_path)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
