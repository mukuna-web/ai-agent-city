"""Knowledge graph for shared and individual agent knowledge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class KnowledgeNode:
    id: str
    type: str  # "agent", "location", "resource", "building", "skill"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    source: str
    target: str
    relation: str  # "knows", "owns", "located_at", "trades_with", "trusts"
    weight: float = 1.0  # confidence / strength


class KnowledgeGraph:
    """Simple graph-based knowledge store for agents."""

    def __init__(self):
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []

    def add_node(self, node_id: str, node_type: str, **properties) -> KnowledgeNode:
        node = KnowledgeNode(id=node_id, type=node_type, properties=properties)
        self.nodes[node_id] = node
        return node

    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        edge = KnowledgeEdge(source=source, target=target, relation=relation, weight=weight)
        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self.nodes.get(node_id)

    def get_relations(self, node_id: str, relation: Optional[str] = None) -> list[KnowledgeEdge]:
        edges = [e for e in self.edges if e.source == node_id or e.target == node_id]
        if relation:
            edges = [e for e in edges if e.relation == relation]
        return edges

    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> list[str]:
        neighbors = set()
        for edge in self.get_relations(node_id, relation):
            if edge.source == node_id:
                neighbors.add(edge.target)
            else:
                neighbors.add(edge.source)
        return list(neighbors)

    def update_edge_weight(self, source: str, target: str, relation: str, new_weight: float):
        for edge in self.edges:
            if edge.source == source and edge.target == target and edge.relation == relation:
                edge.weight = new_weight
                return
        self.add_edge(source, target, relation, new_weight)

    def remove_weak_edges(self, threshold: float = 0.1):
        self.edges = [e for e in self.edges if e.weight >= threshold]

    def stats(self) -> dict:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "node_types": list(set(n.type for n in self.nodes.values())),
            "relation_types": list(set(e.relation for e in self.edges)),
        }


class SharedKnowledge:
    """City-wide knowledge base that all agents can query."""

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.resource_locations: dict[str, list[tuple[int, int]]] = {}
        self.building_locations: dict[str, list[tuple[int, int]]] = {}
        self.agent_reputations: dict[str, float] = {}

    def register_resource(self, resource_name: str, x: int, y: int):
        if resource_name not in self.resource_locations:
            self.resource_locations[resource_name] = []
        pos = (x, y)
        if pos not in self.resource_locations[resource_name]:
            self.resource_locations[resource_name].append(pos)

    def register_building(self, building_name: str, x: int, y: int):
        if building_name not in self.building_locations:
            self.building_locations[building_name] = []
        pos = (x, y)
        if pos not in self.building_locations[building_name]:
            self.building_locations[building_name].append(pos)

    def find_nearest_resource(self, resource_name: str, x: int, y: int) -> Optional[tuple[int, int]]:
        locations = self.resource_locations.get(resource_name, [])
        if not locations:
            return None
        return min(locations, key=lambda p: abs(p[0] - x) + abs(p[1] - y))

    def find_nearest_building(self, building_name: str, x: int, y: int) -> Optional[tuple[int, int]]:
        locations = self.building_locations.get(building_name, [])
        if not locations:
            return None
        return min(locations, key=lambda p: abs(p[0] - x) + abs(p[1] - y))

    def update_reputation(self, agent_id: str, delta: float):
        current = self.agent_reputations.get(agent_id, 0.5)
        self.agent_reputations[agent_id] = max(0.0, min(1.0, current + delta))

    def get_reputation(self, agent_id: str) -> float:
        return self.agent_reputations.get(agent_id, 0.5)
