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
# Date: 2026-04-27

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple

try:
    from torch_geometric.nn import GATv2Conv
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False
    GATv2Conv = None

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class DiffusionGraphConv(nn.Module):
    """
    Diffusion Graph Convolution Layer (DCRNN / Graph WaveNet style).
    
    Models traffic flow as a Markov diffusion process in two directions:
    1. Forward Random Walk (Downstream flow): P_f = D_o^{-1} * A
    2. Backward Random Walk (Upstream wave/congestion): P_b = D_i^{-1} * A^T
    3. Adaptive Adjacency: Learns hidden correlations not in static map.
    """

    def __init__(self, in_channels: int, out_channels: int, diffusion_steps: int = 2):
        super(DiffusionGraphConv, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.diffusion_steps = diffusion_steps
        
        # Number of matrices: Forward(K) + Backward(K) + Adaptive(1) + Identity(1)
        # Total transition matrices = 2 * diffusion_steps + 1
        num_matrices = 2 * diffusion_steps + 1
        self.weights = nn.Parameter(torch.FloatTensor(num_matrices * in_channels, out_channels))
        self.bias = nn.Parameter(torch.FloatTensor(out_channels))
        
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.weights)
        nn.init.zeros_(self.bias)

    @staticmethod
    def compute_transition_matrices(
        num_nodes: int, 
        edge_index: torch.Tensor, 
        edge_weight: Optional[torch.Tensor] = None,
        device: torch.device = torch.device('cpu')
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes forward and backward normalized random-walk transition matrices.
        """
        if edge_index.numel() == 0 or edge_index.size(1) == 0:
            # Fallback for disconnected graph
            identity = torch.eye(num_nodes, device=device)
            return identity, identity

        # Build dense adjacency
        adj = torch.zeros((num_nodes, num_nodes), device=device)
        src, dst = edge_index[0], edge_index[1]
        
        weights = edge_weight if edge_weight is not None else torch.ones_like(src, dtype=torch.float, device=device)
        adj.index_put_((src, dst), weights)

        # Forward transition (Out-degree normalization)
        d_out = adj.sum(dim=1)
        d_out_inv = torch.where(d_out > 0, 1.0 / d_out, torch.zeros_like(d_out))
        p_forward = torch.diag(d_out_inv) @ adj

        # Backward transition (In-degree normalization of transpose)
        adj_t = adj.t()
        d_in = adj_t.sum(dim=1)
        d_in_inv = torch.where(d_in > 0, 1.0 / d_in, torch.zeros_like(d_in))
        p_backward = torch.diag(d_in_inv) @ adj_t

        return p_forward, p_backward

    def forward(
        self, 
        x: torch.Tensor, 
        p_forward: torch.Tensor, 
        p_backward: torch.Tensor, 
        adaptive_adj: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            x: Node features [Batch, Num_Nodes, In_Channels]
            p_forward: Forward random-walk matrix [Num_Nodes, Num_Nodes]
            p_backward: Backward random-walk matrix [Num_Nodes, Num_Nodes]
            adaptive_adj: Learned adaptive adjacency [Num_Nodes, Num_Nodes]
        Returns:
            out: Convolved node features [Batch, Num_Nodes, Out_Channels]
        """
        batch_size, num_nodes, in_channels = x.shape
        states: List[torch.Tensor] = [x]  # Order 0: Identity (current node state)

        # Forward Walk Powers: P_f^k * X
        x_f = x
        for _ in range(self.diffusion_steps):
            # Matrix multiplication over node dimension: [Batch, N, C] with [N, N] -> [Batch, N, C]
            x_f = torch.einsum('nm,bmc->bnc', p_forward, x_f)
            states.append(x_f)

        # Backward Walk Powers: P_b^k * X
        x_b = x
        for _ in range(self.diffusion_steps):
            x_b = torch.einsum('nm,bmc->bnc', p_backward, x_b)
            states.append(x_b)

        # Adaptive Transition (if available)
        if adaptive_adj is not None:
            x_adp = torch.einsum('nm,bmc->bnc', adaptive_adj, x)
            # Match number of states expected by weights
            if len(states) < (2 * self.diffusion_steps + 1):
                states.append(x_adp)
            else:
                # Replace last state with adaptive combination
                states[-1] = 0.5 * (states[-1] + x_adp)

        # Concatenate diffusion states along feature dimension: [Batch, N, Num_Matrices * In_Channels]
        h = torch.cat(states[: (2 * self.diffusion_steps + 1)], dim=-1)

        # Linear projection to output channels: [Batch, N, Out_Channels]
        out = torch.einsum('bnc,cd->bnd', h, self.weights) + self.bias
        return out


class GatedTemporalConv(nn.Module):
    """
    Gated Temporal Convolution (Gated TCN).
    Applies 1D causal convolutions with GLU (Gated Linear Unit): tanh(W1*x) * sigmoid(W2*x)
    """

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dropout: float = 0.1):
        super(GatedTemporalConv, self).__init__()
        self.kernel_size = kernel_size
        padding = (kernel_size - 1)  # Causal padding

        self.conv_filter = nn.Conv1d(in_channels, out_channels, kernel_size, padding=padding)
        self.conv_gate = nn.Conv1d(in_channels, out_channels, kernel_size, padding=padding)
        self.dropout = nn.Dropout(dropout)
        
        # Residual connection
        self.residual = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [Batch, In_Channels, Seq_Len]
        Returns:
            out: [Batch, Out_Channels, Seq_Len]
        """
        # Trim right side for strict causality
        filt = torch.tanh(self.conv_filter(x))
        gate = torch.sigmoid(self.conv_gate(x))
        
        if self.kernel_size > 1:
            filt = filt[:, :, :-(self.kernel_size - 1)]
            gate = gate[:, :, :-(self.kernel_size - 1)]
            
        gated_out = filt * gate
        res = self.residual(x)
        
        return self.dropout(gated_out + res)


class DiffusionGATv2(nn.Module):
    """
    Hybrid Spatio-Temporal Diffusion and Dynamic Attention Network.
    
    Combines:
    1. Bidirectional Graph Diffusion (Graph WaveNet / DCRNN) for macroscopic flow spreading.
    2. Adaptive Node Embeddings (E1, E2) for latent topological correlation learning.
    3. Gated Temporal Convolutions for fast multi-scale temporal filtering.
    4. GATv2 Dynamic Spatial Attention with observability masking.
    
    This enables precise state extrapolation to the entire city even when only
    a single node has an active sensor.
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
        
        # 1. Adaptive Graph Embeddings (E1, E2)
        self.node_emb1 = nn.Parameter(torch.randn(num_nodes, adaptive_dim))
        self.node_emb2 = nn.Parameter(torch.randn(num_nodes, adaptive_dim))
        
        # 2. Diffusion Graph Convolution Block
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

        # 4. Gated Temporal Convolution
        self.gated_tcn = GatedTemporalConv(out_channels, out_channels, kernel_size=3, dropout=dropout)
        
        # 5. Layer Normalization & Dropout
        self.norm1 = nn.LayerNorm(hidden_channels)
        self.norm2 = nn.LayerNorm(out_channels)
        self.dropout = nn.Dropout(dropout)
        
        # 6. Observability Gate (Conditions extrapolation on active sensor presence)
        self.mask_gate = nn.Sequential(
            nn.Linear(out_channels + 1, out_channels),
            nn.Sigmoid()
        )

    def get_adaptive_adjacency(self) -> torch.Tensor:
        """
        Generates softmax-normalized adaptive adjacency matrix:
        A_adp = Softmax(ReLU(E1 * E2^T))
        """
        adp = F.relu(torch.mm(self.node_emb1, self.node_emb2.t()))
        return F.softmax(adp, dim=-1)

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
        
        # 1. Compute dynamic transition matrices
        # If global speeds exist, scale edge weights by physical velocity factor
        edge_weights = None
        if global_speed_factor is not None and edge_index.numel() > 0:
            if global_speed_factor.dim() == 1 and global_speed_factor.size(0) == edge_index.size(1):
                edge_weights = F.relu(global_speed_factor)
        
        p_forward, p_backward = DiffusionGraphConv.compute_transition_matrices(
            num_nodes=num_nodes,
            edge_index=edge_index,
            edge_weight=edge_weights,
            device=device
        )
        
        # 2. Get adaptive graph
        adp_adj = self.get_adaptive_adjacency().to(device)
        
        # 3. Diffusion Step 1
        h1 = self.diff_conv1(x, p_forward, p_backward, adaptive_adj=adp_adj)
        h1 = self.norm1(F.relu(h1))
        h1 = self.dropout(h1)
        
        # 4. Diffusion Step 2
        h2 = self.diff_conv2(h1, p_forward, p_backward, adaptive_adj=adp_adj)
        h2 = self.norm2(F.relu(h2))
        
        # 5. Spatial GATv2 Attention Refinement
        if self.gat_layer is not None and edge_index.numel() > 0:
            # Flatten batch for PyG Conv: [Batch * N, C]
            h_flat = h2.view(-1, self.out_channels)
            
            # Replicate edge_index across batch
            if batch_size == 1:
                batch_edge_index = edge_index.to(device)
            else:
                edge_list = []
                for b in range(batch_size):
                    edge_list.append(edge_index.to(device) + (b * num_nodes))
                batch_edge_index = torch.cat(edge_list, dim=1)
                
            gat_out = self.gat_layer(h_flat, batch_edge_index)
            h_spatial = gat_out.view(batch_size, num_nodes, self.out_channels)
            h2 = self.norm2(h2 + self.dropout(F.elu(h_spatial)))
            
        # 6. Observability Gate (Calibração Dinâmica)
        # If mask is provided, modulates features to anchor ground truth
        if observability_mask is not None:
            mask = observability_mask.to(device)
            if mask.dim() == 1:
                mask = mask.unsqueeze(0).unsqueeze(-1).expand(batch_size, num_nodes, 1)
            elif mask.dim() == 2:
                mask = mask.unsqueeze(-1)
                
            # Gate combines diffusion features with sensor presence confidence
            gate_input = torch.cat([h2, mask.float()], dim=-1)
            gate = self.mask_gate(gate_input)
            
            # Ground truth anchors keep full strength; virtual nodes receive diffused state
            h2 = h2 * gate + x * mask.float() if in_dim == self.out_channels else h2 * gate

        return h2, adp_adj
