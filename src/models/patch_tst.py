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
# File: src/models/patch_tst.py
# Author: Gabriel Moraes
# Date: 2026-04-27

import math
import torch
import torch.nn as nn


class PatchTST(nn.Module):
    """
    Patch Time Series Transformer for Imputation.
    
    Reference: "A Time Series is Worth 64 Words" (Nie et al., ICLR 2023).
    
    Architecture:
    1. Patch Embedding: Splits the time series into non-overlapping (or overlapping)
       patches via Conv1d, similar to how ViT treats image patches.
    2. Positional Encoding: Learnable position embeddings for patch order.
    3. Transformer Encoder: Standard multi-head self-attention on patches.
    4. Reconstruction Head: Projects back to original sequence length.
    
    Key Properties:
    - Channel Independence: Each feature is processed independently (CI mode).
    - Single optimizer, single loss (MSE) — no adversarial instability.
    - Memory efficient: patches reduce sequence length → O(n/p) attention.
    """

    def __init__(
        self,
        feature_dim: int = 4,
        seq_len: int = 24,
        patch_len: int = 8,
        stride: int = 4,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 128,
        dropout: float = 0.1,
    ):
        """
        Args:
            feature_dim: Number of input features (channels).
            seq_len: Length of the input time series.
            patch_len: Length of each patch.
            stride: Stride for patch extraction (stride < patch_len = overlap).
            d_model: Transformer hidden dimension.
            n_heads: Number of attention heads.
            n_layers: Number of Transformer encoder layers.
            d_ff: Feed-forward dimension in Transformer.
            dropout: Dropout rate.
        """
        super().__init__()

        self.feature_dim = feature_dim
        self.seq_len = seq_len
        self.patch_len = patch_len
        self.stride = stride
        self.d_model = d_model

        # ── Number of patches ──
        self.num_patches = max(1, (seq_len - patch_len) // stride + 1)

        # ── Patch Embedding ──
        # Projects each patch [patch_len] → [d_model]
        self.patch_embedding = nn.Linear(patch_len, d_model)

        # ── Positional Encoding (Learnable) ──
        self.position_embedding = nn.Parameter(
            torch.randn(1, self.num_patches, d_model) * 0.02
        )

        # ── Transformer Encoder ──
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers
        )

        # ── Layer Norm ──
        self.layer_norm = nn.LayerNorm(d_model)

        # ── Reconstruction Head ──
        # From [num_patches, d_model] → [seq_len]
        self.reconstruction_head = nn.Linear(self.num_patches * d_model, seq_len)

        # ── Dropout ──
        self.dropout = nn.Dropout(dropout)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier Uniform initialization for linear layers."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def _create_patches(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extracts patches from the input sequence using unfold.
        
        Args:
            x: [Batch, SeqLen] (single channel)
            
        Returns:
            patches: [Batch, NumPatches, PatchLen]
        """
        # Pad if necessary to ensure we get enough patches
        pad_len = max(0, self.patch_len + (self.num_patches - 1) * self.stride - x.shape[-1])
        if pad_len > 0:
            x = nn.functional.pad(x, (0, pad_len), mode='reflect')

        # unfold: extract sliding windows
        patches = x.unfold(dimension=-1, size=self.patch_len, step=self.stride)
        return patches  # [Batch, NumPatches, PatchLen]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for imputation.
        
        Args:
            x: [Batch, SeqLen, FeatureDim]
            
        Returns:
            reconstructed: [Batch, SeqLen, FeatureDim]
        """
        batch_size = x.shape[0]
        
        # ── Channel Independence: process each feature separately ──
        outputs = []
        
        for ch in range(self.feature_dim):
            # Extract single channel: [Batch, SeqLen]
            x_ch = x[:, :, ch]
            
            # Create patches: [Batch, NumPatches, PatchLen]
            patches = self._create_patches(x_ch)
            
            # Embed patches: [Batch, NumPatches, d_model]
            patch_emb = self.patch_embedding(patches)
            
            # Add positional encoding
            patch_emb = patch_emb + self.position_embedding
            patch_emb = self.dropout(patch_emb)
            
            # Transformer encoding: [Batch, NumPatches, d_model]
            encoded = self.transformer_encoder(patch_emb)
            encoded = self.layer_norm(encoded)
            
            # Flatten and reconstruct: [Batch, NumPatches * d_model] → [Batch, SeqLen]
            flat = encoded.reshape(batch_size, -1)
            reconstructed_ch = self.reconstruction_head(flat)
            
            outputs.append(reconstructed_ch)
        
        # Stack channels: [Batch, SeqLen, FeatureDim]
        reconstructed = torch.stack(outputs, dim=-1)
        
        return reconstructed
