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
# File: src/models/diffusion_gatv2.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple

from src.utils.graph_utils import (
    compute_random_walk_transition_matrices,
    batch_offset_edge_index
)
from src.blocks.graph_blocks import (
    DiffusionGraphConv,
    AdaptiveAdjacency,
    ObservabilityGate,
    GatedTemporalConv
)

try:
    from torch_geometric.nn import GATv2Conv
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False
    GATv2Conv = None


class DiffusionGATv2(nn.Module):
    """
    Hybrid Spatio-Temporal Diffusion and Dynamic Attention Network.
    
    A pure neural model conforming to SOLID principles:
    1. Bidirectional Graph Diffusion (DiffusionGraphConv) for macroscopic flow spreading.
    2. Adaptive Node Embeddings (AdaptiveAdjacency) for latent topological correlation learning.
    3. GATv2 Dynamic Spatial Attention with observability masking.
    4. Sensor Observability Gating (ObservabilityGate) for calibrating ground truth anchors.
    """

    def __init__(
        self,
        num_nodes: int,
        in_channels: int = 32,
        hidden_channels: int = 64,
        out_channels: int = 32,
        diffusion_steps: int = 2,
        adaptive_dim: int = 16,
        gat_heads: int = 2,
        dropout: float = 0.1
    ):
        super(DiffusionGATv2, self).__init__()
        self.num_nodes = num_nodes
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.diffusion_steps = diffusion_steps
        self.gat_heads = gat_heads
        
        # 1. Adaptive Graph Adjacency Block (SRP/DIP)
        self.adaptive_block = AdaptiveAdjacency(num_nodes=num_nodes, adaptive_dim=adaptive_dim)
        
        # 2. Diffusion Graph Convolution Blocks (SRP/DIP)
        self.diff_conv1 = DiffusionGraphConv(in_channels, hidden_channels, diffusion_steps)
        self.diff_conv2 = DiffusionGraphConv(hidden_channels, out_channels, diffusion_steps)
        
        # 3. Dynamic Attention Layer (GATv2)
        if PYG_AVAILABLE:
            self.gat_layer = GATv2Conv(
                in_channels=out_channels,
                out_channels=out_channels // gat_heads,
                heads=gat_heads,
                concat=True,
                dropout=dropout
            )
        else:
            self.gat_layer = None

        # 4. Layer Normalization & Dropout
        self.norm1 = nn.LayerNorm(hidden_channels)
        self.norm2 = nn.LayerNorm(out_channels)
        self.dropout = nn.Dropout(dropout)
        
        # 5. Observability Gate Block (SRP/ISP)
        self.observability_gate = ObservabilityGate(in_channels=out_channels, out_channels=out_channels)

    def get_adaptive_adjacency(self) -> torch.Tensor:
        """
        Generates softmax-normalized adaptive adjacency matrix:
        A_adp = Softmax(ReLU(E1 * E2^T))
        """
        return self.adaptive_block()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        observability_mask: Optional[torch.Tensor] = None,
        global_speed_factor: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Node features [Batch, Num_Nodes, In_Channels] or [Num_Nodes, In_Channels]
            edge_index: Graph connectivity [2, Num_Edges]
            observability_mask: Mask of active sensors [Num_Nodes] or [Batch, Num_Nodes, 1]
                                (1 = Ground Truth Sensor, 0 = Unobserved Virtual Node)
            global_speed_factor: Optional macroscopic speed weights for edges/nodes.
            
        Returns:
            extrapolated_embedding: [Batch, Num_Nodes, Out_Channels]
            adaptive_adj: Learned adjacency matrix [Num_Nodes, Num_Nodes]
        """
        # Ensure 3D batch dimension [Batch, Num_Nodes, In_Channels]
        if x.dim() == 2:
            x = x.unsqueeze(0)
            
        batch_size, num_nodes, in_dim = x.shape
        device = x.device
        
        # 1. Compute dynamic transition matrices via graph utilities (SRP)
        edge_weights = None
        if global_speed_factor is not None and edge_index.numel() > 0:
            if global_speed_factor.dim() == 1 and global_speed_factor.size(0) == edge_index.size(1):
                edge_weights = F.relu(global_speed_factor)
        
        p_forward, p_backward = compute_random_walk_transition_matrices(
            num_nodes=num_nodes,
            edge_index=edge_index,
            edge_weight=edge_weights,
            device=device
        )
        
        # 2. Get adaptive graph
        adp_adj = self.adaptive_block().to(device)
        
        # 3. Diffusion Step 1
        h1 = self.diff_conv1(x, p_forward, p_backward, adaptive_adj=adp_adj)
        h1 = self.norm1(F.relu(h1))
        h1 = self.dropout(h1)
        
        # 4. Diffusion Step 2
        h2 = self.diff_conv2(h1, p_forward, p_backward, adaptive_adj=adp_adj)
        h2 = self.norm2(F.relu(h2))
        
        # 5. Spatial GATv2 Attention Refinement
        if self.gat_layer is not None and edge_index.numel() > 0:
            h_flat = h2.view(-1, self.out_channels)
            batch_edge_index = batch_offset_edge_index(edge_index, batch_size, num_nodes, device)
                
            gat_out = self.gat_layer(h_flat, batch_edge_index)
            h_spatial = gat_out.view(batch_size, num_nodes, self.out_channels)
            h2 = self.norm2(h2 + self.dropout(F.elu(h_spatial)))
            
        # 6. Observability Gate (Dynamic Calibration & Anchor preservation)
        h2 = self.observability_gate(h=h2, x_raw=x, observability_mask=observability_mask)

        return h2, adp_adj


__all__ = [
    "DiffusionGATv2",
    "DiffusionGraphConv",
    "AdaptiveAdjacency",
    "ObservabilityGate",
    "GatedTemporalConv"
]
