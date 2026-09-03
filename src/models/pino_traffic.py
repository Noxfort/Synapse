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
# File: src/models/pino_traffic.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from typing import Optional, Dict, Tuple, Union, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.interfaces.physics import IFundamentalDiagram
from src.physics.fundamental_diagrams import GreenshieldsDiagram
from src.physics.continuum import SpatialGraphConservation
from src.blocks.spectral_blocks import SpectralConv1d, SpectralConv2d

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class PINOTrafficFlow1D(nn.Module):
    """
    Physics-Informed Neural Operator (PINO) for Macroscopic Traffic Flow.
    
    Combines:
    1. Fourier Neural Operator (FNO) Spectral Convolutions for fast continuous simulation.
    2. Hydrodynamic Lighthill-Whitham-Richards (LWR) PDE residual constraints.
    3. Pluggable integration with FusionPipeline and spatial road graphs.
    """

    def __init__(
        self,
        in_channels: int = 32,
        hidden_dim: int = 64,
        modes: int = 16,
        num_layers: int = 4,
        v_free_default: float = 60.0,
        k_jam_default: float = 120.0,
        q_max_default: float = 1800.0,
        fundamental_diagram: Optional[IFundamentalDiagram] = None,
        **kwargs
    ):
        super().__init__()
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.modes = modes
        self.num_layers = num_layers

        self.v_free_default = v_free_default
        self.k_jam_default = k_jam_default
        self.q_max_default = q_max_default

        self.fundamental_diagram = fundamental_diagram or GreenshieldsDiagram()
        self.graph_conservation = SpatialGraphConservation()

        # 1. Lifting projection: In -> Hidden Width
        self.p_lifting = nn.Linear(in_channels, hidden_dim)

        # 2. Stack of Fourier Neural Operator Blocks
        self.spectral_layers = nn.ModuleList([
            SpectralConv1d(hidden_dim, hidden_dim, modes) for _ in range(num_layers)
        ])
        self.w_layers = nn.ModuleList([
            nn.Conv1d(hidden_dim, hidden_dim, 1) for _ in range(num_layers)
        ])

        # 3. Projection Head: Hidden Width -> Physical States [density, speed, flow]
        self.physical_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 3)
        )

        # 4. Latent Physics Gate: Refines embedding with physical states
        self.physics_gate = nn.Sequential(
            nn.Linear(in_channels + 3, in_channels),
            nn.Sigmoid()
        )

        # 5. Parameter adapter for local road variation
        self.param_adapter = nn.Sequential(
            nn.Linear(in_channels, 2),
            nn.Tanh()
        )

    def forward_operator(self, x: torch.Tensor) -> torch.Tensor:
        """
        FNO core operator forward pass:
        Args:
            x: [Batch, Num_Nodes, in_channels]
        Returns:
            x_latent: [Batch, Num_Nodes, hidden_dim]
        """
        # Lifting: [Batch, Num_Nodes, Hidden] -> [Batch, Hidden, Num_Nodes]
        x_lifted = self.p_lifting(x).permute(0, 2, 1)

        for spec_conv, w_conv in zip(self.spectral_layers, self.w_layers):
            x1 = spec_conv(x_lifted)
            x2 = w_conv(x_lifted)
            x_lifted = F.gelu(x1 + x2)

        # [Batch, Num_Nodes, Hidden]
        return x_lifted.permute(0, 2, 1)

    def project_physical_states(self, x_latent: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Projects latent operator representations to non-negative [k, v, q].
        """
        raw_physics = self.physical_head(x_latent)
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
        Compatible with FusionPipeline:
        Args:
            x_embedding: [Batch, Num_Nodes, in_channels] or [Num_Nodes, in_channels]
            edge_index: Graph connectivity [2, Num_Edges]
            global_velocities: Optional macroscopic speeds
            dt: Time differential
        Returns:
            refined_embedding: [Batch, Num_Nodes, in_channels]
            metrics: Dictionary containing physical variables and PDE residuals
        """
        if x_embedding.dim() == 2:
            x_embedding = x_embedding.unsqueeze(0)

        batch_size, num_nodes, _ = x_embedding.shape
        device = x_embedding.device

        # 1. Neural Operator Pass
        x_latent = self.forward_operator(x_embedding)

        # 2. Physical State Projections
        k_est, v_est, q_est = self.project_physical_states(x_latent)

        # 3. Learnable road parameter offsets
        offsets = self.param_adapter(x_embedding)
        v_free = self.v_free_default * (1.0 + 0.2 * offsets[:, :, 0:1])
        k_jam = self.k_jam_default * (1.0 + 0.2 * offsets[:, :, 1:2])

        # 4. Macro velocity boundary constraint
        if global_velocities is not None:
            g_vel = global_velocities.to(device)
            if g_vel.dim() == 1:
                g_vel = g_vel.unsqueeze(0).unsqueeze(-1).expand(batch_size, num_nodes, 1)
            elif g_vel.dim() == 2 and g_vel.shape[-1] != 1:
                g_vel = g_vel.unsqueeze(-1)
            valid_mask = (g_vel > 0).float()
            v_est = v_est * (1.0 - 0.5 * valid_mask) + g_vel * (0.5 * valid_mask)

        # 5. Hydrodynamic LWR Residual & Spatial Conservation
        q_theory = self.fundamental_diagram.compute_flow(k_est, v_free, k_jam)
        res_flow = torch.abs(q_est - q_theory)

        if edge_index is not None and edge_index.numel() > 0:
            res_conservation = self.graph_conservation.compute_loss(q_est, edge_index)
        else:
            res_conservation = torch.tensor(0.0, device=device)

        physics_residual = res_flow.mean() + 0.1 * res_conservation

        # 6. Latent Gate Injection
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


class SpectralFeatureExtractor(nn.Module):
    """
    Fourier Spectral Feature Extractor.
    Drop-in replacement for TimesNet in PeakClassifierAgent and PeakPipeline.
    Extracts periodic patterns across multi-scale frequency bands using FFT.
    """

    def __init__(
        self,
        enc_in: int = 2,
        d_model: int = 64,
        seq_len: int = 2048,
        modes: int = 32,
        **kwargs
    ):
        super().__init__()
        self.enc_in = enc_in
        self.d_model = d_model
        self.seq_len = seq_len

        self.conv_in = nn.Conv1d(enc_in, d_model, 1)
        self.spectral_conv = SpectralConv1d(d_model, d_model, modes1=modes)
        self.fc_out = nn.Sequential(
            nn.Conv1d(d_model, d_model, 3, padding=1),
            nn.GELU(),
            nn.Conv1d(d_model, enc_in, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor [Batch, SeqLen, Channels] or [Batch, Channels, SeqLen]
        Returns:
            features: [Batch, SeqLen, Channels]
        """
        is_seq_first = False
        if x.dim() == 3 and x.size(1) != self.enc_in and x.size(2) == self.enc_in:
            x = x.permute(0, 2, 1)
            is_seq_first = True

        h = self.conv_in(x)
        h_spec = self.spectral_conv(h)
        out = self.fc_out(F.gelu(h + h_spec))

        if is_seq_first:
            out = out.permute(0, 2, 1)

        return out


__all__ = [
    "SpectralConv1d",
    "SpectralConv2d",
    "PINOTrafficFlow1D",
    "SpectralFeatureExtractor"
]
