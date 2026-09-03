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
# File: src/blocks/graph_blocks.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Optional, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from src.utils.graph_utils import compute_random_walk_transition_matrices


class DiffusionGraphConv(nn.Module):
    """
    Diffusion Graph Convolution Layer (DCRNN / Graph WaveNet style).
    
    Models traffic flow as a Markov diffusion process across:
    1. Forward Random Walk (Downstream flow): P_f
    2. Backward Random Walk (Upstream congestion wave): P_b
    3. Adaptive Adjacency: Learns hidden correlations not in static map.
    """

    def __init__(self, in_channels: int, out_channels: int, diffusion_steps: int = 2):
        super(DiffusionGraphConv, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.diffusion_steps = diffusion_steps
        
        # Number of matrices: Forward(K) + Backward(K) + Adaptive(1) + Identity(1)
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
        Proxy method to `compute_random_walk_transition_matrices` in `src.utils.graph_utils`
        maintained for backward compatibility.
        """
        return compute_random_walk_transition_matrices(
            num_nodes=num_nodes,
            edge_index=edge_index,
            edge_weight=edge_weight,
            device=device
        )

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
            if len(states) < (2 * self.diffusion_steps + 1):
                states.append(x_adp)
            else:
                states[-1] = 0.5 * (states[-1] + x_adp)

        # Concatenate diffusion states along feature dimension
        h = torch.cat(states[: (2 * self.diffusion_steps + 1)], dim=-1)

        # Linear projection to output channels
        out = torch.einsum('bnc,cd->bnd', h, self.weights) + self.bias
        return out


class AdaptiveAdjacency(nn.Module):
    """
    Learnable Adaptive Graph Adjacency Block.
    
    Learns node embeddings (E1, E2) to infer latent topological dependencies:
    A_adp = Softmax(ReLU(E1 * E2^T))
    """

    def __init__(self, num_nodes: int, adaptive_dim: int = 16):
        super(AdaptiveAdjacency, self).__init__()
        self.num_nodes = num_nodes
        self.adaptive_dim = adaptive_dim
        self.node_emb1 = nn.Parameter(torch.randn(num_nodes, adaptive_dim))
        self.node_emb2 = nn.Parameter(torch.randn(num_nodes, adaptive_dim))
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.node_emb1)
        nn.init.xavier_uniform_(self.node_emb2)

    def forward(self) -> torch.Tensor:
        """
        Generates softmax-normalized adaptive adjacency matrix:
        A_adp = Softmax(ReLU(E1 * E2^T))
        """
        adp = F.relu(torch.mm(self.node_emb1, self.node_emb2.t()))
        return F.softmax(adp, dim=-1)


class ObservabilityGate(nn.Module):
    """
    Dynamic Observability Gate Layer.
    
    Conditions and blends extrapolated virtual representations with ground truth anchors:
    - Active sensors (mask=1): Preserves ground-truth state observations.
    - Unobserved virtual nodes (mask=0): Modulated by confidence gate over diffused states.
    """

    def __init__(self, in_channels: int, out_channels: int):
        super(ObservabilityGate, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.mask_gate = nn.Sequential(
            nn.Linear(out_channels + 1, out_channels),
            nn.Sigmoid()
        )

    def forward(
        self,
        h: torch.Tensor,
        x_raw: torch.Tensor,
        observability_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            h: Diffused/processed representations [Batch, Num_Nodes, Out_Channels]
            x_raw: Raw input representations [Batch, Num_Nodes, In_Channels]
            observability_mask: Binary mask of active sensors [Num_Nodes] or [Batch, Num_Nodes, 1]
        Returns:
            Gated calibrated features [Batch, Num_Nodes, Out_Channels]
        """
        if observability_mask is None:
            return h

        batch_size, num_nodes, out_dim = h.shape
        in_dim = x_raw.shape[-1]
        device = h.device

        mask = observability_mask.to(device)
        if mask.dim() == 1:
            mask = mask.unsqueeze(0).unsqueeze(-1).expand(batch_size, num_nodes, 1)
        elif mask.dim() == 2:
            mask = mask.unsqueeze(-1)

        # Gate combines feature representations with sensor presence confidence
        gate_input = torch.cat([h, mask.float()], dim=-1)
        gate = self.mask_gate(gate_input)

        # Ground truth anchors retain full strength; virtual nodes receive diffused state
        if in_dim == out_dim:
            return h * gate + x_raw * mask.float()
        return h * gate


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
        filt = torch.tanh(self.conv_filter(x))
        gate = torch.sigmoid(self.conv_gate(x))
        
        if self.kernel_size > 1:
            filt = filt[:, :, :-(self.kernel_size - 1)]
            gate = gate[:, :, :-(self.kernel_size - 1)]
            
        gated_out = filt * gate
        res = self.residual(x)
        
        return self.dropout(gated_out + res)
