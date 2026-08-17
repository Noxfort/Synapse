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
# File: src/models/pinn_traffic_flow.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Optional, Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from src.physics.physics_interfaces import IFundamentalDiagram
from src.physics.fundamental_diagrams import GreenshieldsDiagram
from src.physics.continuum import SpatialGraphConservation

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class PINNTrafficFlow(nn.Module):
    """
    Physics-Informed Neural Network (PINN) for Traffic Flow Consistency.
    
    A clean neural projector and physics gate responsible for:
    1. Mapping latent spatial embeddings to physical traffic variables [k (density), v (speed), q (flow)].
    2. Modulating parameters via learnable road parameter adapters.
    3. Blending physical states back into latent representations via a gated mechanism.
    4. Delegating theoretical flow calculations to injected IFundamentalDiagram.
    """

    def __init__(
        self,
        in_channels: int = 32,
        hidden_dim: int = 64,
        v_free_default: float = 60.0,   # km/h free-flow speed
        k_jam_default: float = 120.0,   # veh/km jam density
        q_max_default: float = 1800.0,  # veh/h/lane maximum capacity
        fundamental_diagram: Optional[IFundamentalDiagram] = None
    ):
        super(PINNTrafficFlow, self).__init__()
        
        self.v_free_default = v_free_default
        self.k_jam_default = k_jam_default
        self.q_max_default = q_max_default
        
        # Pluggable fundamental diagram strategy (DIP/OCP)
        self.fundamental_diagram = fundamental_diagram or GreenshieldsDiagram()
        self.graph_conservation = SpatialGraphConservation()
        
        # 1. State Projector: Extrapolated Latent -> Physical Traffic Variables [k, v, q]
        self.physical_head = nn.Sequential(
            nn.Linear(in_channels, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 3)
        )
        
        # 2. Physics Correction Gate: Blends neural estimation with physics
        self.physics_gate = nn.Sequential(
            nn.Linear(in_channels + 3, in_channels),
            nn.Sigmoid()
        )
        
        # 3. Learnable road parameter offsets
        self.param_adapter = nn.Sequential(
            nn.Linear(in_channels, 2),
            nn.Tanh()
        )

    def compute_fundamental_flow(
        self, 
        density: torch.Tensor, 
        v_free: torch.Tensor, 
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        """
        Computes theoretical traffic flow using the injected fundamental diagram strategy.
        """
        return self.fundamental_diagram.compute_flow(density, v_free, k_jam)

    def project_physical_states(self, x_embedding: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Projects latent representations into non-negative physical variables [density, speed, flow].
        """
        raw_physics = self.physical_head(x_embedding)
        k_est = F.softplus(raw_physics[:, :, 0:1])
        v_est = F.softplus(raw_physics[:, :, 1:2])
        q_est = F.softplus(raw_physics[:, :, 2:3])
        return k_est, v_est, q_est

    def forward(
        self,
        x_embedding: torch.Tensor,
        edge_index: Optional[torch.Tensor] = None,
        global_velocities: Optional[torch.Tensor] = None,
        dt: float = 1.0
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Args:
            x_embedding: Node embedding from diffusion [Batch, Num_Nodes, Channels]
            edge_index: Graph connectivity [2, Num_Edges]
            global_velocities: Optional macroscopic speeds for nodes/edges
            dt: Time step differential
            
        Returns:
            physically_refined_embedding: [Batch, Num_Nodes, Channels]
            physics_metrics: Dictionary with estimated [density, speed, flow, physics_residual]
        """
        if x_embedding.dim() == 2:
            x_embedding = x_embedding.unsqueeze(0)
            
        batch_size, num_nodes, in_dim = x_embedding.shape
        device = x_embedding.device
        
        # 1. Project to raw physical variables
        k_est, v_est, q_est = self.project_physical_states(x_embedding)
        
        # 2. Modulate parameters using road parameter offsets
        offsets = self.param_adapter(x_embedding)
        v_free = self.v_free_default * (1.0 + 0.2 * offsets[:, :, 0:1])
        k_jam = self.k_jam_default * (1.0 + 0.2 * offsets[:, :, 1:2])
        
        # 3. Macro Velocity Boundary Constraint
        if global_velocities is not None:
            g_vel = global_velocities.to(device)
            if g_vel.dim() == 1:
                g_vel = g_vel.unsqueeze(0).unsqueeze(-1).expand(batch_size, num_nodes, 1)
            elif g_vel.dim() == 2 and g_vel.shape[-1] != 1:
                g_vel = g_vel.unsqueeze(-1)
                
            valid_mask = (g_vel > 0).float()
            v_est = v_est * (1.0 - 0.5 * valid_mask) + g_vel * (0.5 * valid_mask)

        # 4. Fundamental Flow Residual
        q_theory = self.compute_fundamental_flow(k_est, v_free, k_jam)
        res_flow = torch.abs(q_est - q_theory)
        
        # Spatial Graph Conservation Residual via physics module
        if edge_index is not None and edge_index.numel() > 0:
            res_conservation = self.graph_conservation.compute_loss(q_est, edge_index)
        else:
            res_conservation = torch.tensor(0.0, device=device)
            
        physics_residual = res_flow.mean() + 0.1 * res_conservation
        
        # 5. Physics Gate Injection into Latent Representation
        physics_vector = torch.cat([k_est, v_est, q_est], dim=-1)
        gate_input = torch.cat([x_embedding, physics_vector], dim=-1)
        gate = self.physics_gate(gate_input)
        
        refined_embedding = x_embedding * gate
        
        metrics = {
            "density": k_est.squeeze(-1),
            "speed": v_est.squeeze(-1),
            "flow": q_est.squeeze(-1),
            "physics_residual": physics_residual
        }
        
        return refined_embedding, metrics
