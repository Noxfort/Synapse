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
# File: src/services/imputer_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Optional
from torch.amp import autocast, GradScaler

from src.models.patch_tst import PatchTST
from src.utils.normalization import TensorNormalizer


class ImputerTrainer:
    """
    Dedicated Training Routine & Optimizer for Imputer Neural Models.
    Implements masked reconstruction training with AMP.
    """

    def __init__(
        self,
        model: PatchTST,
        learning_rate: float = 0.001,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        self.criterion = nn.MSELoss()
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu')

    def to(self, device: Any) -> 'ImputerTrainer':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu')
        return self

    def train_step(self, batch_data: torch.Tensor) -> float:
        """
        Single masked training step.
        """
        self.model.train()

        x = batch_data.to(self.device)
        if torch.isnan(x).any():
            x = torch.nan_to_num(x, nan=0.0)

        if not x.is_contiguous():
            x = x.contiguous()

        if x.ndim == 2:
            x = x.unsqueeze(-1)

        mask = torch.rand_like(x) < 0.15
        x_masked = x.clone()
        x_masked[mask] = 0.0

        self.optimizer.zero_grad()
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        x_masked_norm, mean, std = TensorNormalizer.zscore_norm(x_masked, seq_dim=1)
        x_norm = (x - mean) / (std + TensorNormalizer.EPS)

        with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
            reconstructed_norm = self.model(x_masked_norm)
            if mask.any():
                loss = self.criterion(reconstructed_norm[mask], x_norm[mask])
            else:
                loss = self.criterion(reconstructed_norm, x_norm)

        if not torch.isfinite(loss):
            self.scaler.update()
            return 100.0

        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()
