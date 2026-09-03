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
# File: src/models/pi_vae_tcn.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Tuple, Optional, Any, Union
import torch
import torch.nn as nn
from src.blocks.temporal_blocks import TemporalBlock, CausalConv1d

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class PIVAETCN(nn.Module):
    """
    Pure Variational Autoencoder with Temporal Convolutional Network backbone (VAE-TCN).
    
    A clean neural architecture responsible exclusively for:
    1. Temporal Encoder: Dilated Causal TCN compresses time series into latent representations.
    2. Stochastic Latent Manifold: Reparameterization (Mu, LogVar) -> z ~ N(mu, sigma^2).
    3. Temporal Decoder: Symmetrical Causal TCN reconstructs the signal.
    
    Adheres strictly to SOLID: pure computational graph, zero hardcoded training losses.
    """
    def __init__(
        self,
        input_channels: int,
        hidden_channels: int = 64,
        latent_channels: int = 32,
        kernel_size: int = 3,
        dropout: float = 0.2,
        max_acceleration: float = 10.0,
        physics_loss_engine: Optional[Any] = None
    ):
        super().__init__()
        
        self.input_channels = input_channels
        self.hidden_channels = hidden_channels
        self.latent_channels = latent_channels
        self.max_acceleration = max_acceleration
        
        # Optional physics loss engine reference for backward compatibility
        self.physics_engine = physics_loss_engine
        
        # --- 1. Temporal Encoder ---
        self.encoder_tcn = nn.Sequential(
            TemporalBlock(input_channels, hidden_channels, kernel_size, dilation=1, dropout=dropout),
            TemporalBlock(hidden_channels, hidden_channels, kernel_size, dilation=2, dropout=dropout),
            TemporalBlock(hidden_channels, hidden_channels, kernel_size, dilation=4, dropout=dropout)
        )
        
        # Latent Projections
        self.fc_mu = nn.Conv1d(hidden_channels, latent_channels, 1)
        self.fc_logvar = nn.Conv1d(hidden_channels, latent_channels, 1)

        # --- 2. Temporal Decoder ---
        self.fc_decode = nn.Conv1d(latent_channels, hidden_channels, 1)
        
        self.decoder_tcn = nn.Sequential(
            TemporalBlock(hidden_channels, hidden_channels, kernel_size, dilation=4, dropout=dropout),
            TemporalBlock(hidden_channels, hidden_channels, kernel_size, dilation=2, dropout=dropout),
            TemporalBlock(hidden_channels, hidden_channels, kernel_size, dilation=1, dropout=dropout)
        )
        
        # Final Output Projection
        self.final_layer = nn.Conv1d(hidden_channels, input_channels, 1)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        VAE Reparameterization Trick: z = mu + std * epsilon
        """
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(
        self,
        x: torch.Tensor,
        return_physics_residuals: bool = False
    ) -> Union[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]]:
        """
        Forward pass through VAE-TCN.
        
        Args:
            x: Input tensor [Batch, Channels, Sequence_Length]
            return_physics_residuals: If True, computes physics residuals via TrafficPhysicsLoss
            
        Returns:
            recon: Reconstructed sequence [Batch, Channels, Sequence_Length]
            mu: Latent mean [Batch, Latent_Channels, Sequence_Length]
            logvar: Latent log variance [Batch, Latent_Channels, Sequence_Length]
        """
        # 1. Encode
        enc_out = self.encoder_tcn(x)
        
        # 2. Latent Distribution Parameters
        mu = self.fc_mu(enc_out)
        logvar = self.fc_logvar(enc_out)
        
        # 3. Stochastic Sampling
        z = self.reparameterize(mu, logvar)
        
        # 4. Decode
        dec_in = self.fc_decode(z)
        dec_out = self.decoder_tcn(dec_in)
        
        # 5. Output Reconstruction
        recon = self.final_layer(dec_out)
        
        if return_physics_residuals:
            residuals = self.compute_physics_residuals(recon, orig_x=x)
            return recon, mu, logvar, residuals
            
        return recon, mu, logvar

    def compute_physics_residuals(
        self,
        recon: torch.Tensor,
        orig_x: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """Computes physics loss residuals on reconstructed sequence."""
        from src.physics.traffic_loss import TrafficPhysicsLoss
        engine = self.physics_engine or TrafficPhysicsLoss(max_acceleration=self.max_acceleration)
        return engine.compute_losses(recon, orig_x=orig_x)

