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
# File: src/physics/continuum.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from src.interfaces.physics import IPhysicsConstraint


class ContinuumConservation(nn.Module):
    """
    Hydrodynamic Continuum Traffic Model (LWR - Lighthill-Whitham-Richards).
    Enforces consistency between Flow (q), Density (rho/k), and Velocity (v):
        q_expected = rho * v
        Residual: SmoothL1(q / scale, q_expected / scale)
    """

    def __init__(self, penalty_scale: float = 1.0, use_smooth_l1: bool = True):
        super().__init__()
        self.penalty_scale = penalty_scale
        self.use_smooth_l1 = use_smooth_l1

    def compute_residual(
        self,
        q: torch.Tensor,
        v: torch.Tensor,
        rho: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Args:
            q: Flow tensor [Batch, SeqLen] or [Batch, Nodes]
            v: Velocity tensor [Batch, SeqLen] or [Batch, Nodes]
            rho: Density tensor [Batch, SeqLen] or [Batch, Nodes]
        Returns:
            loss_conservation: Scalar conservation residual.
        """
        device = q.device
        q_expected = torch.relu(rho) * torch.relu(v)
        
        if self.use_smooth_l1:
            scale = torch.clamp(torch.mean(torch.abs(q) + 1.0), min=1.0)
            loss = F.smooth_l1_loss(q / scale, q_expected / scale)
        else:
            loss = torch.mean((q - q_expected) ** 2)
            
        return self.penalty_scale * loss


class SpatialGraphConservation(nn.Module):
    """
    Spatial Flow Conservation along Road Graph Edges (Kirchhoff Law for Traffic):
    Computes spatial divergence along directed graph edges:
        div(q) = inflow(node) - outflow(node)
    """

    def __init__(self, penalty_scale: float = 1.0):
        super().__init__()
        self.penalty_scale = penalty_scale

    def compute_residual(
        self,
        flow: torch.Tensor,
        edge_index: Optional[torch.Tensor] = None,
        **kwargs
    ) -> torch.Tensor:
        """
        Args:
            flow: Estimated flow tensor [Batch, Num_Nodes, 1] or [Batch, Num_Nodes]
            edge_index: Graph connectivity [2, Num_Edges]
        Returns:
            loss_spatial_conservation: Mean spatial divergence error.
        """
        device = flow.device
        
        if edge_index is None or edge_index.numel() == 0:
            return torch.tensor(0.0, device=device)
            
        if flow.dim() == 2:
            flow = flow.unsqueeze(-1)
            
        src = edge_index[0].to(device)
        dst = edge_index[1].to(device)
        
        # Outflow from source node, inflow into destination node
        flow_out = flow[:, src, :]
        flow_in = flow[:, dst, :]
        
        # Spatial flow difference across edges
        flow_diff = torch.abs(flow_in - flow_out)
        
        # Aggregate divergence at destination nodes
        res_conservation = torch.zeros_like(flow)
        res_conservation.index_add_(1, dst, flow_diff)
        
        loss = res_conservation.mean()
        return self.penalty_scale * loss

    def compute_loss(self, flow: torch.Tensor, edge_index: Optional[torch.Tensor] = None, **kwargs) -> torch.Tensor:
        """Alias for compute_residual."""
        return self.compute_residual(flow, edge_index, **kwargs)

    def forward(self, flow: torch.Tensor, edge_index: Optional[torch.Tensor] = None, **kwargs) -> torch.Tensor:
        """Forward pass delegates to compute_residual."""
        return self.compute_residual(flow, edge_index, **kwargs)
