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
# File: src/memory/topology_memory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional


class TopologyMemory:
    """
    Topology Memory for Dynamic Graph Connectivity and Edge Features.
    
    Responsibilities:
    - Tracks road network graph connectivity (COO edge indices and adjacency matrices).
    - Supports real-time topological events (road closures, construction, dynamic edge weight changes).
    - Exports PyG-compatible edge_index and weight tensors directly on target devices.
    """

    def __init__(self, num_nodes: int = 0, device: Optional[torch.device] = None):
        self.num_nodes = num_nodes
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Edge dict: (src, dst) -> (weight, is_active)
        self.edges: Dict[Tuple[int, int], Tuple[float, bool]] = {}

    def set_graph(
        self,
        num_nodes: int,
        edge_list: List[Tuple[int, int]],
        edge_weights: Optional[List[float]] = None
    ) -> None:
        """
        Initializes graph connectivity.
        """
        self.num_nodes = num_nodes
        self.edges.clear()
        
        for i, (src, dst) in enumerate(edge_list):
            w = float(edge_weights[i]) if edge_weights and i < len(edge_weights) else 1.0
            self.edges[(src, dst)] = (w, True)

    def update_edge_weight(self, src: int, dst: int, weight: float) -> bool:
        """
        Updates the physical weight (e.g. capacity or free-flow speed) of an existing edge.
        """
        if (src, dst) in self.edges:
            _, is_active = self.edges[(src, dst)]
            self.edges[(src, dst)] = (float(weight), is_active)
            return True
        return False

    def disable_edge(self, src: int, dst: int) -> bool:
        """
        Disables an edge in real-time (e.g. accident or road closure).
        """
        if (src, dst) in self.edges:
            w, _ = self.edges[(src, dst)]
            self.edges[(src, dst)] = (w, False)
            return True
        return False

    def enable_edge(self, src: int, dst: int, weight: Optional[float] = None) -> None:
        """
        Re-enables or adds an edge.
        """
        current_w = weight if weight is not None else 1.0
        if (src, dst) in self.edges and weight is None:
            current_w, _ = self.edges[(src, dst)]
        self.edges[(src, dst)] = (float(current_w), True)

    def get_edge_index_tensor(self, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Returns active edges as PyTorch COO Tensor: [2, Num_Active_Edges].
        """
        target_device = device or self.device
        active_edges = [edge for edge, (_, is_active) in self.edges.items() if is_active]
        
        if not active_edges:
            return torch.empty((2, 0), dtype=torch.long, device=target_device)
            
        src_nodes = [e[0] for e in active_edges]
        dst_nodes = [e[1] for e in active_edges]
        return torch.tensor([src_nodes, dst_nodes], dtype=torch.long, device=target_device)

    def get_edge_weights_tensor(self, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Returns active edge weights as PyTorch Tensor: [Num_Active_Edges].
        """
        target_device = device or self.device
        active_weights = [w for _, (w, is_active) in self.edges.items() if is_active]
        
        if not active_weights:
            return torch.empty((0,), dtype=torch.float32, device=target_device)
            
        return torch.tensor(active_weights, dtype=torch.float32, device=target_device)

    def get_adjacency_matrix(self, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Constructs dense weighted adjacency matrix: [Num_Nodes, Num_Nodes].
        """
        target_device = device or self.device
        adj = torch.zeros((self.num_nodes, self.num_nodes), dtype=torch.float32, device=target_device)
        
        for (src, dst), (w, is_active) in self.edges.items():
            if is_active and src < self.num_nodes and dst < self.num_nodes:
                adj[src, dst] = w
                
        return adj

    def clear(self) -> None:
        """Resets the topology."""
        self.edges.clear()
        self.num_nodes = 0
