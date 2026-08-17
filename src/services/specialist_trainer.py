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
# File: src/services/specialist_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Tuple, Optional
from torch.amp import autocast, GradScaler


class SpecialistTrainer:
    """
    Dedicated Training Routine & Optimizer for Specialist TCN Models.
    """

    def __init__(
        self,
        model: nn.ModuleDict,
        input_dim: int = 1,
        output_dim: int = 32,
        learning_rate: float = 0.001,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.learning_rate = learning_rate

        self.tcn = self.model["tcn"]
        self.decoder = self.model["decoder"] if "decoder" in self.model else None
        self.reconstruction_head = self.model["reconstruction_head"] if "reconstruction_head" in self.model else None

        self.optimizer = optim.Adam(
            [p for p in self.model.parameters() if p.requires_grad] or self.model.parameters(),
            lr=learning_rate
        )
        self.scaler = GradScaler(device='cuda' if torch.cuda.is_available() else 'cpu')
        self.criterion = nn.MSELoss()

        target_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(target_device)

    def _get_current_device(self) -> torch.device:
        try:
            return next(self.tcn.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def to(self, device: Any) -> 'SpecialistTrainer':
        target_device = torch.device(device) if isinstance(device, str) else device
        self.model.to(target_device)
        self.scaler = GradScaler(device='cuda' if target_device.type == 'cuda' else 'cpu')
        return self

    def train_step(self, batch_data: Any) -> float:
        """
        Single training step for TCNAE auto-reconstruction / feature learning.
        """
        # If model is frozen, skip gradient update and return 0.0
        if getattr(self.tcn, "is_frozen", False) or not any(p.requires_grad for p in self.model.parameters()):
            return 0.0

        self.model.train()
        device = self._get_current_device()

        if isinstance(batch_data, (tuple, list)):
            inputs, targets = batch_data
        else:
            inputs, targets = batch_data, batch_data

        inputs = inputs.to(device)
        targets = targets.to(device)

        self.optimizer.zero_grad()
        device_type = device.type if device.type != 'mps' else 'cpu'

        with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
            if inputs.shape[-1] == self.input_dim and inputs.ndim == 3:
                batch_x_t = inputs.permute(0, 2, 1)
            elif inputs.ndim == 2:
                batch_x_t = inputs.unsqueeze(1)
            else:
                batch_x_t = inputs

            # Check if using modern TCNAE Autoencoder
            if hasattr(self.tcn, "encoder") and hasattr(self.tcn, "decoder"):
                reconstructed, embedding = self.tcn(batch_x_t, return_embedding=True)
                
                # If target is matching embedding dimension (e.g. [Batch, output_dim])
                if targets.ndim == 2 and targets.shape[-1] == self.output_dim:
                    loss = self.criterion(embedding, targets)
                elif targets.ndim == 3 and targets.shape[-1] == self.output_dim and self.output_dim != self.input_dim:
                    loss = self.criterion(embedding, targets[:, -1, :])
                else:
                    # Target is reconstruction target [Batch, Channels, SeqLen]
                    if targets.shape[-1] == self.input_dim and targets.ndim == 3:
                        target_t = targets.permute(0, 2, 1)
                    elif targets.ndim == 2 and targets.shape[0] == batch_x_t.shape[0]:
                        target_t = targets.unsqueeze(1)
                    else:
                        target_t = targets
                    loss = self.criterion(reconstructed, target_t)
            else:
                tcn_out = self.tcn(batch_x_t)
                if self.decoder is not None:
                    tcn_out_transposed = tcn_out.transpose(1, 2)
                    embedding = self.decoder(tcn_out_transposed)
                    pred = embedding
                    if targets.shape[-1] == self.input_dim and self.output_dim != self.input_dim:
                        if self.reconstruction_head is not None:
                            pred = self.reconstruction_head(embedding)
                    elif targets.shape[-1] != self.output_dim and targets.shape[1] == self.output_dim:
                        pred = pred.transpose(1, 2)
                else:
                    pred = tcn_out
                loss = self.criterion(pred, targets)

        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()

    def train(self, inputs: torch.Tensor, targets: torch.Tensor, epochs: int = 1, batch_size: int = 32) -> float:
        """
        Multi-batch training loop.
        """
        dataset_size = inputs.size(0)
        total_loss = 0.0
        effective_batch = min(dataset_size, batch_size)
        permutation = torch.randperm(dataset_size)

        for i in range(0, dataset_size, effective_batch):
            indices = permutation[i: i + effective_batch]
            batch_x = inputs[indices]
            batch_y = targets[indices]

            loss = self.train_step((batch_x, batch_y))
            total_loss += loss

        avg_loss = total_loss / max(1, (dataset_size / effective_batch))
        return avg_loss
