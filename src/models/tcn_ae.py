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
# File: src/models/tcn_ae.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional, Union

from src.blocks.temporal_blocks import Chomp1d, TemporalBlock

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class TCNAEEncoder(nn.Module):
    """
    Lightweight Causal TCN Encoder.
    Compresses an input sequence [Batch, Channels, SeqLen] into a latent representation [Batch, LatentDim].
    """
    def __init__(
        self,
        num_inputs: int = 1,
        num_channels: Optional[List[int]] = None,
        latent_dim: int = 32,
        kernel_size: int = 2,
        dropout: float = 0.1
    ):
        super(TCNAEEncoder, self).__init__()
        num_channels = num_channels or [8, 16]
        layers = []
        num_levels = len(num_channels)
        
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i - 1]
            out_channels = num_channels[i]
            padding = (kernel_size - 1) * dilation_size
            layers.append(TemporalBlock(
                n_inputs=in_channels,
                n_outputs=out_channels,
                kernel_size=kernel_size,
                stride=1,
                dilation=dilation_size,
                padding=padding,
                dropout=dropout
            ))
            
        self.network = nn.Sequential(*layers)
        self.latent_proj = nn.Conv1d(num_channels[-1], latent_dim, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Returns:
            latent: [Batch, LatentDim, SeqLen]
        """
        features = self.network(x)
        latent = self.latent_proj(features)
        return latent


class TCNAEDecoder(nn.Module):
    """
    Lightweight Causal TCN Decoder.
    Reconstructs the original physical traffic signals [Batch, OutputDim, SeqLen] from the latent space.
    """
    def __init__(
        self,
        latent_dim: int = 32,
        num_channels: Optional[List[int]] = None,
        num_outputs: int = 1,
        kernel_size: int = 2,
        dropout: float = 0.1
    ):
        super(TCNAEDecoder, self).__init__()
        channels = list(reversed(num_channels or [8, 16]))
        self.input_proj = nn.Conv1d(latent_dim, channels[0], kernel_size=1)
        
        layers = []
        for i in range(len(channels)):
            dilation_size = 2 ** (len(channels) - 1 - i)
            in_channels = channels[i]
            out_channels = channels[i + 1] if i + 1 < len(channels) else channels[-1]
            padding = (kernel_size - 1) * dilation_size
            layers.append(TemporalBlock(
                n_inputs=in_channels,
                n_outputs=out_channels,
                kernel_size=kernel_size,
                stride=1,
                dilation=dilation_size,
                padding=padding,
                dropout=dropout
            ))
            
        self.network = nn.Sequential(*layers)
        self.reconstruct_head = nn.Conv1d(channels[-1], num_outputs, kernel_size=1)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Returns:
            reconstructed: [Batch, OutputDim, SeqLen]
        """
        h = self.input_proj(z)
        features = self.network(h)
        return self.reconstruct_head(features)


class TCNAE(nn.Module):
    """
    Pure Temporal Convolutional Autoencoder (TCN-AE).
    
    A clean neural network architecture for node-level temporal feature extraction and compression:
    - Ultra-compact parameter footprint (~3.000 parameters / < 20 KB VRAM).
    - Causal dilated convolutions guaranteeing zero temporal leakage.
    - Pure computational graph adhering strictly to SOLID.
    """
    def __init__(
        self,
        num_inputs: int = 1,
        num_channels: Optional[List[int]] = None,
        latent_dim: int = 32,
        kernel_size: int = 2,
        dropout: float = 0.1
    ):
        super(TCNAE, self).__init__()
        self.num_inputs = num_inputs
        self.num_channels = num_channels or [8, 16]
        self.latent_dim = latent_dim
        self.kernel_size = kernel_size
        self.dropout = dropout

        self.encoder = TCNAEEncoder(
            num_inputs=num_inputs,
            num_channels=self.num_channels,
            latent_dim=latent_dim,
            kernel_size=kernel_size,
            dropout=dropout
        )
        self.decoder = TCNAEDecoder(
            latent_dim=latent_dim,
            num_channels=self.num_channels,
            num_outputs=num_inputs,
            kernel_size=kernel_size,
            dropout=dropout
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extracts the latent embedding for the sequence.
        
        Args:
            x: Tensor [Batch, Channels, SeqLen]
        Returns:
            z: Latent embedding vector at the last timestep [Batch, LatentDim]
        """
        latent_seq = self.encoder(x)
        return latent_seq[:, :, -1]

    def decode(self, z: torch.Tensor, seq_len: int) -> torch.Tensor:
        """
        Reconstructs the sequence from a latent vector.
        
        Args:
            z: Latent embedding [Batch, LatentDim]
            seq_len: Target sequence length to expand
        Returns:
            reconstructed: [Batch, Channels, SeqLen]
        """
        z_expanded = z.unsqueeze(-1).expand(-1, -1, seq_len)
        return self.decoder(z_expanded)

    def forward(
        self,
        x: torch.Tensor,
        return_embedding: bool = True
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Full Autoencoder forward pass.
        
        Args:
            x: Input tensor [Batch, Channels, SeqLen]
            return_embedding: Whether to return (reconstructed, latent_embedding)
        Returns:
            reconstructed: [Batch, Channels, SeqLen]
            (optional) embedding: [Batch, LatentDim]
        """
        latent_seq = self.encoder(x)
        reconstructed = self.decoder(latent_seq)
        
        if return_embedding:
            embedding = latent_seq[:, :, -1]
            return reconstructed, embedding
        return reconstructed


# Compatibility Alias
TemporalConvNet = TCNAE
