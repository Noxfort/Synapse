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
# File: src/models/wavelet_ae_occ.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# Try importing Kymatio for Wavelet Scattering
try:
    from kymatio.torch import Scattering1D
    KYMATIO_AVAILABLE = True
except ImportError:
    KYMATIO_AVAILABLE = False

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class WaveletSpectralAE(nn.Module):
    """
    Pure Spectral Wavelet Autoencoder (Wavelet-AE).
    
    A clean neural network module responsible exclusively for:
    1. Extracting translation-invariant spectral representations via Wavelet Scattering.
    2. Compressing representations into a latent manifold [Batch, LatentDim].
    3. Decoding back to spectral domain [Batch, ScatDim] and time domain [Batch, InputLen].
    
    Adheres strictly to SOLID: zero statistical anomaly state, zero internal loss calculations.
    """

    def __init__(
        self,
        input_len: int,
        J: int = 2,
        Q: int = 1,
        latent_dim: int = 16
    ):
        super().__init__()
        
        self.input_len = input_len
        self.latent_dim = latent_dim
        
        # --- Padding Strategy to Avoid Border Effects ---
        self.padded_len = 2 ** int(np.ceil(np.log2(input_len)) + 1)
        
        # 1. Wavelet Scattering Setup
        if KYMATIO_AVAILABLE:
            self.scattering = Scattering1D(J=J, shape=(self.padded_len,), Q=Q, T=self.padded_len)
            with torch.no_grad():
                dummy_input = torch.zeros(1, self.padded_len)
                dummy_out = self.scattering(dummy_input)
                self.scat_dim = dummy_out.shape[1] 
            self.using_wavelets = True
        else:
            self.scat_dim = self.padded_len
            self.scattering = nn.Identity()
            self.using_wavelets = False

        # 2. Spectral Encoder (Features -> Latent)
        self.encoder = nn.Sequential(
            nn.Linear(self.scat_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Linear(64, latent_dim)
        )
        
        # 3. Spectral Decoder (Latent -> Wavelet Reconstruction)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Linear(64, self.scat_dim)
        )

        # 4. Time-Domain Reconstruction Head (Latent -> Time Sequence)
        self.time_decoder = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Linear(64, input_len)
        )

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Extracts spectral features and latent representations.
        
        Args:
            x: Input tensor [Batch, Time] or [Batch, Channels, Time]
        Returns:
            feats: Extracted wavelet scattering features [Batch, ScatDim]
            z: Bottleneck latent representations [Batch, LatentDim]
        """
        if x.ndim == 3 and x.shape[-1] == 1: 
            x = x.squeeze(-1)
            
        pad_size = self.padded_len - self.input_len
        if pad_size > 0:
            pad_left = pad_size // 2
            pad_right = pad_size - pad_left
            x_padded = F.pad(x, (pad_left, pad_right), mode='reflect')
        else:
            x_padded = x
        
        if self.using_wavelets:
            feats = self.scattering(x_padded)
            feats = feats.view(x_padded.size(0), -1)
        else:
            feats = x_padded
            
        z = self.encoder(feats)
        return feats, z

    def decode(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Reconstructs both spectral and time-domain signals from latent vector.
        
        Args:
            z: Latent vector [Batch, LatentDim]
        Returns:
            rec_feats: Reconstructed spectral features [Batch, ScatDim]
            time_recon: Reconstructed time-series signal [Batch, InputLen]
        """
        rec_feats = self.decoder(z)
        time_recon = self.time_decoder(z)
        return rec_feats, time_recon

    def forward(
        self,
        x: torch.Tensor,
        return_time_recon: bool = True
    ) -> Union[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        """
        Forward pass.
        
        Args:
            x: Input tensor [Batch, Time]
            return_time_recon: If True, returns time-domain signal reconstruction
        Returns:
            feats: Extracted features [Batch, ScatDim]
            z: Latent vector [Batch, LatentDim]
            rec_feats: Spectral reconstruction [Batch, ScatDim]
            (optional) time_recon: Time-domain reconstruction [Batch, InputLen]
        """
        feats, z = self.encode(x)
        rec_feats, time_recon = self.decode(z)
        
        if return_time_recon:
            return feats, z, rec_feats, time_recon
        return feats, z, rec_feats


# Compatibility Class for existing code references
WaveletAEOCC = WaveletSpectralAE