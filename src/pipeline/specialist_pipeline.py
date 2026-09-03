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
# File: src/pipeline/specialist_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import numpy as np
from typing import List, Any, Optional, Union
from torch.amp import autocast

from src.models.tcn_ae import TCNAE


class SpecialistPipeline:
    """
    Dedicated Neural Pipeline for Temporal Convolutional Autoencoder (TCN-AE) Feature Extraction.
    Encapsulates TCNAE execution, decoding, and embedding generation with device safety and Warmup & Freeze.
    """

    def __init__(
        self,
        model: Optional[nn.ModuleDict] = None,
        input_dim: int = 1,
        output_dim: int = 32,
        num_channels: Optional[List[int]] = None,
        kernel_size: int = 2,
        dropout: float = 0.1,
        device: Optional[torch.device] = None,
        **kwargs: Any
    ):
        self.input_dim = input_dim
        self.output_dim = output_dim
        num_channels = num_channels or [8, 16]

        if model is not None:
            self.model = model
        else:
            tcn = TCNAE(
                num_inputs=input_dim,
                num_channels=num_channels,
                latent_dim=output_dim,
                kernel_size=kernel_size,
                dropout=dropout
            )
            # Retain decoder/reconstruction_head references for backward compatibility
            self.model = nn.ModuleDict({
                "tcn": tcn,
                "decoder": getattr(tcn, "decoder", None),
                "reconstruction_head": getattr(getattr(tcn, "decoder", None), "reconstruct_head", None)
            })

        self.tcn = self.model["tcn"]
        self.decoder = self.model["decoder"] if "decoder" in self.model else None
        self.reconstruction_head = self.model["reconstruction_head"] if "reconstruction_head" in self.model else None

        target_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(target_device)

    def _get_current_device(self) -> torch.device:
        try:
            return next(self.tcn.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def to(self, device: Any) -> 'SpecialistPipeline':
        target_device = torch.device(device) if isinstance(device, str) else device
        self.model.to(target_device)
        return self

    def freeze(self) -> 'SpecialistPipeline':
        """Freezes internal TCNAE weights for zero-cost drift-safe real-time inference."""
        if hasattr(self.tcn, "freeze"):
            self.tcn.freeze()
        else:
            for param in self.model.parameters():
                param.requires_grad = False
            self.model.eval()
        return self

    def unfreeze(self) -> 'SpecialistPipeline':
        """Unfreezes internal TCNAE weights for on-demand recalibration."""
        if hasattr(self.tcn, "unfreeze"):
            self.tcn.unfreeze()
        else:
            for param in self.model.parameters():
                param.requires_grad = True
        return self

    @property
    def is_frozen(self) -> bool:
        if hasattr(self.tcn, "is_frozen"):
            return self.tcn.is_frozen
        return not any(p.requires_grad for p in self.model.parameters())

    def predict(self, input_sequence: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
        """
        Extracts temporal embeddings using AMP and Safe Device placement.
        Auto-handles dimension permutations and returns the final embedding vector (32-dim).
        """
        self.model.eval()
        device = self._get_current_device()

        with torch.no_grad():
            seq = input_sequence
            if getattr(seq, "ndim", 0) == 2 and seq.shape[0] > seq.shape[1]:
                # Typical memory buffer is [Time, Features], TCN needs [Features, Time]
                seq = seq.T

            if isinstance(seq, np.ndarray):
                tensor_x = torch.FloatTensor(seq).to(device)
            elif isinstance(seq, torch.Tensor):
                tensor_x = seq.to(device)
            else:
                tensor_x = torch.tensor(seq, dtype=torch.float).to(device)

            if tensor_x.dim() == 1:
                tensor_x = tensor_x.unsqueeze(0).unsqueeze(0)
            elif tensor_x.dim() == 2:
                tensor_x = tensor_x.unsqueeze(0)

            device_type = device.type if device.type != 'mps' else 'cpu'

            with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
                if isinstance(self.tcn, TCNAE):
                    embedding = self.tcn.encode(tensor_x) # [Batch, LatentDim]
                    output = embedding
                else:
                    tcn_out = self.tcn(tensor_x)
                    if self.decoder is not None:
                        tcn_out_transposed = tcn_out.transpose(1, 2)
                        output = self.decoder(tcn_out_transposed).transpose(1, 2)
                    else:
                        output = tcn_out

            full_seq = output.cpu().float().numpy().squeeze(0)
            if full_seq.ndim == 2:
                return full_seq[:, -1]
            return full_seq
