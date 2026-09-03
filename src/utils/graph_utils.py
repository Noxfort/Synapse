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
# File: src/utils/graph_utils.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Optional, Tuple, List
import torch


def compute_random_walk_transition_matrices(
    num_nodes: int,
    edge_index: torch.Tensor,
    edge_weight: Optional[torch.Tensor] = None,
    device: torch.device = torch.device('cpu')
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Computes forward and backward normalized random-walk transition matrices.
    
    Formulas:
    1. Forward Random Walk (Downstream flow): P_f = D_o^{-1} * A
    2. Backward Random Walk (Upstream wave/congestion): P_b = D_i^{-1} * A^T
    
    Args:
        num_nodes: Total number of nodes in the graph.
        edge_index: Graph connectivity in COO format [2, Num_Edges].
        edge_weight: Optional edge weights [Num_Edges].
        device: Target compute device.
        
    Returns:
        p_forward: Normalized forward transition matrix [Num_Nodes, Num_Nodes].
        p_backward: Normalized backward transition matrix [Num_Nodes, Num_Nodes].
    """
    if edge_index.numel() == 0 or edge_index.size(1) == 0:
        # Fallback for disconnected graph
        identity = torch.eye(num_nodes, device=device)
        return identity, identity

    # Build dense adjacency
    adj = torch.zeros((num_nodes, num_nodes), device=device)
    src, dst = edge_index[0].to(device), edge_index[1].to(device)
    
    weights = edge_weight.to(device) if edge_weight is not None else torch.ones_like(src, dtype=torch.float, device=device)
    adj.index_put_((src, dst), weights)

    # Forward transition (Out-degree normalization: P_f = D_out^{-1} * A)
    d_out = adj.sum(dim=1)
    d_out_inv = torch.where(d_out > 0, 1.0 / d_out, torch.zeros_like(d_out))
    p_forward = torch.diag(d_out_inv) @ adj

    # Backward transition (In-degree normalization of transpose: P_b = D_in^{-1} * A^T)
    adj_t = adj.t()
    d_in = adj_t.sum(dim=1)
    d_in_inv = torch.where(d_in > 0, 1.0 / d_in, torch.zeros_like(d_in))
    p_backward = torch.diag(d_in_inv) @ adj_t

    return p_forward, p_backward


def batch_offset_edge_index(
    edge_index: torch.Tensor,
    batch_size: int,
    num_nodes: int,
    device: torch.device = torch.device('cpu')
) -> torch.Tensor:
    """
    Replicates and offsets COO edge_index across multiple graphs in a mini-batch.
    
    Args:
        edge_index: Graph connectivity [2, Num_Edges].
        batch_size: Number of graphs in the batch.
        num_nodes: Number of nodes per graph.
        device: Target device.
        
    Returns:
        batch_edge_index: Disjoint graph edge index [2, Num_Edges * Batch_Size].
    """
    if edge_index.numel() == 0 or edge_index.size(1) == 0:
        return edge_index.to(device)
        
    if batch_size == 1:
        return edge_index.to(device)

    edge_list: List[torch.Tensor] = []
    base_edges = edge_index.to(device)
    for b in range(batch_size):
        edge_list.append(base_edges + (b * num_nodes))
        
    return torch.cat(edge_list, dim=1)
