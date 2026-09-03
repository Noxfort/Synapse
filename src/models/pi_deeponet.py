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
# File: src/models/pi_deeponet.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from typing import Optional, Tuple, Dict, Union
import torch
import torch.nn as nn
import torch.nn.functional as F

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class BranchNet(nn.Module):
    """
    Branch Network for DeepONet.
    Encodes discrete sensor observations u = [v(x_1), v(x_2), ..., v(x_m)]
    into a p-dimensional latent coefficient space.
    """

    def __init__(
        self,
        in_features: int,
        p_latent: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 3,
        dropout: float = 0.05
    ):
        super().__init__()
        layers = []
        curr_dim = in_features

        for i in range(num_layers - 1):
            layers.append(nn.Linear(curr_dim, hidden_dim))
            layers.append(nn.GELU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            curr_dim = hidden_dim

        layers.append(nn.Linear(curr_dim, p_latent))
        self.network = nn.Sequential(*layers)

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        """
        Args:
            u: Sensor observations [Batch, in_features] or [Batch, in_features, SeqLen]
        Returns:
            b: Latent coefficients [Batch, p_latent]
        """
        if u.dim() == 3:
            u = u.flatten(start_dim=1)
        return self.network(u)


class TrunkNet(nn.Module):
    """
    Trunk Network for DeepONet.
    Encodes continuous spatiotemporal query coordinates y = (x, t)
    into p-dimensional continuous basis functions.
    """

    def __init__(
        self,
        coord_dim: int = 2,
        p_latent: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 3
    ):
        super().__init__()
        layers = []
        curr_dim = coord_dim

        for i in range(num_layers - 1):
            layers.append(nn.Linear(curr_dim, hidden_dim))
            layers.append(nn.GELU())
            curr_dim = hidden_dim

        layers.append(nn.Linear(curr_dim, p_latent))
        self.network = nn.Sequential(*layers)

    def forward(self, y: torch.Tensor) -> torch.Tensor:
        """
        Args:
            y: Continuous coordinates [Batch, Num_Queries, coord_dim] or [Num_Queries, coord_dim]
        Returns:
            t: Basis evaluations [Batch, Num_Queries, p_latent] or [Num_Queries, p_latent]
        """
        return self.network(y)


class PIDeepONet(nn.Module):
    """
    Physics-Informed Deep Operator Network (PI-DeepONet).
    
    Learns the solution operator mapping sparse, discrete sensor readings to
    continuous spatiotemporal traffic velocity, density, and flow fields:
        G_theta(u)(x, t) = sum_k (b_k(u) * t_k(x, t)) + b_0
        
    Provides:
    1. Zero-shot continuous evaluation at any (x, t) coordinate.
    2. Physical non-negativity guarantees (Softplus on [density, speed, flow]).
    3. Differentiable PDE residual evaluation for continuum conservation (LWR).
    4. Seamless drop-in compatibility with sliding window sequence reconstruction.
    """

    def __init__(
        self,
        sensor_dim: int = 4,
        coord_dim: int = 2,
        p_latent: int = 64,
        hidden_dim: int = 128,
        out_channels: int = 3,  # [density, speed, flow]
        v_free_default: float = 60.0,
        k_jam_default: float = 120.0,
        feature_dim: Optional[int] = None,
        seq_len: Optional[int] = None,
        **kwargs
    ):
        super().__init__()
        
        # Backward compatibility aliases for ImputerPipeline
        self.sensor_dim = feature_dim or sensor_dim
        self.seq_len = seq_len or 24
        self.coord_dim = coord_dim
        self.p_latent = p_latent
        self.out_channels = out_channels
        
        self.v_free_default = v_free_default
        self.k_jam_default = k_jam_default

        effective_sensor_in = self.sensor_dim * (self.seq_len if seq_len else 1)
        self.branch = BranchNet(in_features=effective_sensor_in, p_latent=p_latent * out_channels, hidden_dim=hidden_dim)
        self.trunk = TrunkNet(coord_dim=coord_dim, p_latent=p_latent * out_channels, hidden_dim=hidden_dim)
        
        # Learnable scalar biases per output channel
        self.bias = nn.Parameter(torch.zeros(out_channels))

        # Linear projection head when used as a direct sequence transformer/imputer
        self.seq_reconstruction_head = nn.Sequential(
            nn.Linear(out_channels, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, self.sensor_dim)
        )

    def forward(
        self,
        u: torch.Tensor,
        y: Optional[torch.Tensor] = None,
        return_physics_residual: bool = False
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, Dict[str, torch.Tensor]]]:
        """
        Args:
            u: Sensor observations tensor:
               - [Batch, Num_Sensors]
               - [Batch, SeqLen, Channels]
               - [Batch, Channels, SeqLen]
            y: Optional query coordinates [Batch, Num_Queries, coord_dim] or [Num_Queries, coord_dim].
               If None, synthesizes a continuous uniform (x, t) grid matching input sequence dimensions.
            return_physics_residual: If True, computes differentiable LWR PDE residual.
               
        Returns:
            state: Physical state tensor or reconstructed sequence.
        """
        device = u.device
        
        # Standardize input shapes
        if u.dim() == 2:
            batch_size = u.size(0)
            u_flat = u
            is_seq_mode = False
        elif u.dim() == 3:
            batch_size = u.size(0)
            # If shape is [Batch, Channels, SeqLen], permute to [Batch, SeqLen, Channels]
            if u.size(1) == self.sensor_dim and u.size(2) != self.sensor_dim:
                u_seq = u.permute(0, 2, 1)
            else:
                u_seq = u
            u_flat = u_seq.flatten(start_dim=1)
            is_seq_mode = True
        else:
            raise ValueError(f"Unsupported input dimension: {u.dim()}")

        # 1. Synthesize default (x, t) query coordinates if not provided
        if y is None:
            num_t = u.size(1) if (u.dim() == 3 and not (u.size(1) == self.sensor_dim and u.size(2) != self.sensor_dim)) else (u.size(2) if u.dim() == 3 else self.seq_len)
            t_coords = torch.linspace(0.0, 1.0, num_t, device=device)
            x_coords = torch.linspace(0.0, 1.0, 1, device=device)
            grid_t, grid_x = torch.meshgrid(t_coords, x_coords, indexing="ij")
            y = torch.stack([grid_x.flatten(), grid_t.flatten()], dim=-1).unsqueeze(0).expand(batch_size, -1, -1)

        if y.dim() == 2:
            y = y.unsqueeze(0).expand(batch_size, -1, -1)

        num_queries = y.size(1)

        # 2. Branch & Trunk Forward Passes
        b = self.branch(u_flat)  # [Batch, p_latent * out_channels]
        t = self.trunk(y)        # [Batch, Num_Queries, p_latent * out_channels]

        b = b.view(batch_size, 1, self.out_channels, self.p_latent)
        t = t.view(batch_size, num_queries, self.out_channels, self.p_latent)

        # 3. Inner Product Operator Fusion
        # sum over p_latent: [Batch, Num_Queries, Out_Channels]
        raw_output = torch.sum(b * t, dim=-1) + self.bias

        # 4. Enforce Physical Non-Negativity: [density, speed, flow] >= 0
        phys_output = F.softplus(raw_output)

        # 5. Direct Sequence Mode (for Imputer compatibility)
        if is_seq_mode and y.size(1) == u_seq.size(1):
            reconstructed_seq = self.seq_reconstruction_head(phys_output)
            # Match original tensor layout
            if u.dim() == 3 and u.size(1) == self.sensor_dim and u.size(2) != self.sensor_dim:
                final_output = reconstructed_seq.permute(0, 2, 1)
            else:
                final_output = reconstructed_seq
        else:
            final_output = phys_output

        if return_physics_residual:
            residuals = self.compute_pde_residual(phys_output, y)
            return final_output, residuals

        return final_output

    def compute_pde_residual(self, phys_output: torch.Tensor, coords: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Computes hydrodynamic LWR (Lighthill-Whitham-Richards) conservation residuals:
            q_expected = density * speed
            Residual = |flow - density * speed|
        """
        density = phys_output[:, :, 0]
        speed = phys_output[:, :, 1]
        flow = phys_output[:, :, 2] if phys_output.size(-1) >= 3 else (density * speed)

        q_theory = density * speed
        res_conservation = torch.mean(torch.abs(flow - q_theory))

        return {
            "conservation_residual": res_conservation,
            "mean_density": density.mean(),
            "mean_speed": speed.mean(),
            "mean_flow": flow.mean()
        }
