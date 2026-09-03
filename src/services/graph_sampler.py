# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/services/graph_sampler.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Graph Sampler Service — Structural Subgraph Extraction.

Adheres to Single Responsibility Principle (SRP) by isolating graph traversal
and subgraph sampling logic from model training and hyperparameter search.
"""

import random
import logging
from typing import List, Tuple, Dict, Set
from src.domain.entities import MapEdge, MapNode
from src.domain.model_contracts import IGraphSampler

logger = logging.getLogger("Synapse.Services.GraphSampler")


class BfsGraphSampler(IGraphSampler):
    """
    Extracts connected subgraphs from road networks using Breadth-First Search (BFS).
    """

    def sample_subgraph(
        self,
        edges: List[MapEdge],
        nodes: List[MapNode],
        min_edges: int = 5,
        max_edges: int = 30,
    ) -> Tuple[List[MapEdge], List[MapNode]]:
        """
        Performs BFS expansion from a random seed edge to form a connected subgraph.

        Args:
            edges: Full list of map edges.
            nodes: Full list of map nodes.
            min_edges: Minimum number of edges desired in the subgraph.
            max_edges: Maximum number of edges desired in the subgraph.

        Returns:
            Tuple of (sampled_edges, sampled_nodes).
        """
        if not edges:
            return [], []

        if len(edges) <= min_edges:
            return list(edges), list(nodes)

        # Build junction connectivity map
        junction_map: Dict[str, List[MapEdge]] = {}
        for e in edges:
            junction_map.setdefault(e.from_node, []).append(e)
            junction_map.setdefault(e.to_node, []).append(e)

        target = random.randint(min_edges, min(max_edges, len(edges)))
        seed = random.choice(edges)

        visited: Set[str] = {seed.id}
        result_edges: List[MapEdge] = [seed]
        frontier: Set[str] = {seed.from_node, seed.to_node}

        while len(result_edges) < target and frontier:
            junction = random.choice(list(frontier))
            frontier.discard(junction)

            for neighbor in junction_map.get(junction, []):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    result_edges.append(neighbor)
                    frontier.add(neighbor.from_node)
                    frontier.add(neighbor.to_node)
                    if len(result_edges) >= target:
                        break

        # Collect unique nodes participating in the extracted edges
        node_ids: Set[str] = set()
        for e in result_edges:
            node_ids.add(e.from_node)
            node_ids.add(e.to_node)

        node_lookup = {n.id: n for n in nodes}
        result_nodes = [node_lookup[nid] for nid in node_ids if nid in node_lookup]

        return result_edges, result_nodes
