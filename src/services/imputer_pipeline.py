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
# File: src/services/imputer_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
import logging
from typing import Any, Optional
from torch.amp import autocast

from src.models.patch_tst import PatchTST
from src.utils.normalization import TensorNormalizer

logger = logging.getLogger("Synapse.ImputerPipeline")


class ImputerPipeline:
    """
    Dedicated Neural Pipeline for Gap Imputation and Time-Series Reconstruction.
    Encapsulates PatchTST chunking, sliding windows, and Z-Score signal restoration.
    """

    def __init__(
        self,
        model: Optional[PatchTST] = None,
        feature_dim: int = 4,
        seq_len: int = 24,
        patch_len: int = 8,
        stride: int = 4,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 128,
        dropout: float = 0.1,
        device: Optional[torch.device] = None,
        **kwargs: Any
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.seq_len = seq_len
        self.feature_dim = feature_dim

        if model is not None:
            self.model = model
        else:
            self.model = PatchTST(
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

        self.model.to(self.device)

    def to(self, device: Any) -> 'ImputerPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        return self

    def reconstruct(self, incomplete_seq: np.ndarray, chunk_size: int = 4096) -> np.ndarray:
        """
        Uses PatchTST to reconstruct missing values (NaNs) in multivariate sequences.
        """
        self.model.eval()

        working_seq = incomplete_seq.copy()
        mask = np.isnan(working_seq)
        working_seq[mask] = 0.0  # Zero-fill for numerical stability

        is_2d = (working_seq.ndim == 2)
        working_seq = np.ascontiguousarray(working_seq, dtype=np.float32)

        reconstructed_results = []
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with torch.no_grad():
            if is_2d:
                total_length = working_seq.shape[0]
                for i in range(0, total_length, self.seq_len):
                    chunk = working_seq[i:i + self.seq_len]

                    # Pad if chunk is shorter than seq_len
                    if chunk.shape[0] < self.seq_len:
                        pad_rows = self.seq_len - chunk.shape[0]
                        chunk = np.pad(chunk, ((0, pad_rows), (0, 0)), mode='reflect')

                    tensor_x = torch.from_numpy(chunk[np.newaxis, :, :]).to(self.device)
                    tensor_x_norm, mean, std = TensorNormalizer.zscore_norm(tensor_x, seq_dim=1)

                    with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                        x_reconstructed_norm = self.model(tensor_x_norm)

                    x_reconstructed = TensorNormalizer.zscore_denorm(x_reconstructed_norm.float(), mean, std)
                    recon_np = x_reconstructed.cpu().float().numpy().squeeze(0)

                    actual_len = min(self.seq_len, total_length - i)
                    reconstructed_results.append(recon_np[:actual_len])

                    del tensor_x, x_reconstructed, x_reconstructed_norm
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()

                reconstructed = np.concatenate(reconstructed_results, axis=0)
            else:
                batch_size_3d = 128
                for i in range(0, working_seq.shape[0], batch_size_3d):
                    chunk = working_seq[i:i + batch_size_3d]
                    tensor_x = torch.from_numpy(chunk).to(self.device)

                    tensor_x_norm, mean, std = TensorNormalizer.zscore_norm(tensor_x, seq_dim=1)
                    with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                        x_reconstructed_norm = self.model(tensor_x_norm)

                    x_reconstructed = TensorNormalizer.zscore_denorm(x_reconstructed_norm.float(), mean, std)
                    reconstructed_results.append(x_reconstructed.cpu().float().numpy())

                    del tensor_x, x_reconstructed, x_reconstructed_norm
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()

                reconstructed = np.concatenate(reconstructed_results, axis=0)

        # Patch only missing (NaN) positions
        final_output = incomplete_seq.copy()
        final_output[mask] = reconstructed[mask]
        return final_output
