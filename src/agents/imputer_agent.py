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
# File: src/agents/imputer_agent.py
# Author: Gabriel Moraes
# Date: 2026-02-28

import logging
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Any, Dict
from torch.amp import autocast, GradScaler

from src.agents.base_agent import BaseAgent
from src.models.patch_tst import PatchTST
from src.utils.normalization import TensorNormalizer

logger = logging.getLogger(__name__)


class ImputerAgent(BaseAgent):
    """
    The Imputer Agent ('O Reconstrutor').
    
    Responsibilities:
    1. Data Recovery: Fills long gaps (NaNs) in sensor time series.
    2. Reconstruction: Learns normal temporal patterns for gap-filling.
    
    Architecture:
    - Wraps the PatchTST model (Patch Time Series Transformer).
    - Single optimizer, single loss (MSE) — stable training.
    - Channel-independent processing for multivariate series.
    
    Replaces the previous TimeGAN implementation for improved stability,
    lower VRAM usage, and elimination of adversarial training instability.
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
        learning_rate: float = 0.001,
        # Legacy params (accepted but ignored for backward compat)
        hidden_dim: int = None,
        num_layers: int = None,
    ):
        """
        Args:
            feature_dim: Number of input features per timestep.
            seq_len: Length of the time series window.
            patch_len: Length of each patch for the Transformer.
            stride: Stride for patch extraction.
            d_model: Transformer hidden dimension.
            n_heads: Number of attention heads.
            n_layers: Number of Transformer encoder layers.
            d_ff: Feed-forward dimension.
            dropout: Dropout rate.
            learning_rate: Learning rate for Adam optimizer.
            hidden_dim: (LEGACY - ignored) Kept for backward compatibility.
            num_layers: (LEGACY - ignored) Kept for backward compatibility.
        """
        # 1. Create the PatchTST Model
        model = PatchTST(
            feature_dim=feature_dim,
            seq_len=seq_len,
            patch_len=patch_len,
            stride=stride,
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            d_ff=d_ff,
            dropout=dropout,
        )

        # 2. Base Init
        super().__init__(model=model, name="ImputerAgent")

        # 3. Attributes
        self.feature_dim = feature_dim
        self.seq_len = seq_len

        # 4. Single Optimizer (no adversarial dual-optimizer)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        self.criterion = nn.MSELoss()

        # 5. AMP Scaler
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu')

        # Move to device
        self.model.to(self.device)

    def inference(self, input_data: Any) -> Any:
        """Standard Interface: Reconstructs missing values."""
        return self.impute(input_data)

    def impute(self, incomplete_seq: np.ndarray, chunk_size: int = 4096) -> np.ndarray:
        """
        Uses PatchTST to fill gaps in a sequence.
        
        Args:
            incomplete_seq: Numpy array containing NaNs. Shape: [SeqLen, Features] or [Batch, SeqLen, Features].
            chunk_size: Maximum sequence length to process at once.
            
        Returns:
            np.ndarray with NaNs replaced by reconstructed values.
        """
        self.model.eval()

        # --- Pre-processing: Handle NaNs & Layout ---
        working_seq = incomplete_seq.copy()
        mask = np.isnan(working_seq)
        working_seq[mask] = 0.0  # Zero-fill for stability

        is_2d = (working_seq.ndim == 2)
        working_seq = np.ascontiguousarray(working_seq, dtype=np.float32)

        reconstructed_results = []

        with torch.no_grad():
            if is_2d:
                # [TotalLen, Features] → process in sliding windows of seq_len
                total_length = working_seq.shape[0]
                logger.info(f"[{self.name}] Starting chunked imputation. Total: {total_length}, Window: {self.seq_len}")

                for i in range(0, total_length, self.seq_len):
                    chunk = working_seq[i:i + self.seq_len]

                    # Pad if chunk is shorter than seq_len
                    if chunk.shape[0] < self.seq_len:
                        pad_rows = self.seq_len - chunk.shape[0]
                        chunk = np.pad(chunk, ((0, pad_rows), (0, 0)), mode='reflect')

                    # [SeqLen, Feat] → [1, SeqLen, Feat]
                    tensor_x = torch.from_numpy(chunk[np.newaxis, :, :]).to(self.device)
                    
                    # Normalize before transformer (sequence is dim=1)
                    tensor_x_norm, mean, std = TensorNormalizer.zscore_norm(tensor_x, seq_dim=1)
                    x_reconstructed_norm = self.model(tensor_x_norm)
                    x_reconstructed = TensorNormalizer.zscore_denorm(x_reconstructed_norm, mean, std)

                    recon_np = x_reconstructed.cpu().float().numpy().squeeze(0)

                    # Trim padding
                    actual_len = min(self.seq_len, total_length - i)
                    reconstructed_results.append(recon_np[:actual_len])

                    del tensor_x, x_reconstructed
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()

                reconstructed = np.concatenate(reconstructed_results, axis=0)
            else:
                # Already 3D [Batch, SeqLen, Feat] → process in batch chunks
                batch_size_3d = 128
                for i in range(0, working_seq.shape[0], batch_size_3d):
                    chunk = working_seq[i:i + batch_size_3d]
                    tensor_x = torch.from_numpy(chunk).to(self.device)

                    # Normalize before transformer
                    tensor_x_norm, mean, std = TensorNormalizer.zscore_norm(tensor_x, seq_dim=1)
                    x_reconstructed_norm = self.model(tensor_x_norm)
                    x_reconstructed = TensorNormalizer.zscore_denorm(x_reconstructed_norm, mean, std)
                    
                    reconstructed_results.append(x_reconstructed.cpu().float().numpy())

                    del tensor_x, x_reconstructed
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()

                reconstructed = np.concatenate(reconstructed_results, axis=0)

        # --- Post-processing: Patch only NaN positions ---
        final_output = incomplete_seq.copy()
        final_output[mask] = reconstructed[mask]

        logger.info(f"[{self.name}] Imputation completed successfully.")
        return final_output

    def train_step(self, batch_data: torch.Tensor) -> float:
        """
        Single training step — masked reconstruction.
        
        Strategy:
        1. Randomly mask ~15% of input values.
        2. Forward through PatchTST.
        3. Compute MSE loss on the masked positions only.
        
        Returns:
            float: Training loss value.
        """
        self.model.train()

        # Ensure batch is on device
        x = batch_data.to(self.device)

        # Handle NaNs
        if torch.isnan(x).any():
            x = torch.nan_to_num(x, nan=0.0)

        if not x.is_contiguous():
            x = x.contiguous()

        # Ensure 3D: [Batch, SeqLen, Features]
        if x.ndim == 2:
            x = x.unsqueeze(-1)  # [B, S] → [B, S, 1]

        # --- Create Random Mask (15% masking ratio) ---
        mask = torch.rand_like(x) < 0.15
        x_masked = x.clone()
        x_masked[mask] = 0.0

        self.optimizer.zero_grad()

        device_type = self.device.type if self.device.type != 'mps' else 'cpu'
        
        # Z-Score normalization for proper target scale
        x_masked_norm, mean, std = TensorNormalizer.zscore_norm(x_masked, seq_dim=1)
        x_norm = (x - mean) / (std + TensorNormalizer.EPS)  # Target normalized similarly

        with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
            reconstructed_norm = self.model(x_masked_norm)

            # Loss only on masked positions for better gradient signal
            if mask.any():
                loss = self.criterion(reconstructed_norm[mask], x_norm[mask])
            else:
                loss = self.criterion(reconstructed_norm, x_norm)

        # Safety check
        if not torch.isfinite(loss):
            self.scaler.update()
            return 100.0

        self.scaler.scale(loss).backward()

        # Gradient clipping
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()