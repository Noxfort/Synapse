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
# File: src/trainer/cartographer_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Cartographer Trainer — Dedicated Training Routine for Graph Matching Models.

Adheres strictly to SOLID:
- Single Responsibility Principle (SRP): Encapsulates forward/backward passes,
  loss computation, mixed precision, and optimization.
- Dependency Inversion Principle (DIP): Injects model dependency via constructor.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Optional, Callable
from torch.amp import autocast, GradScaler

from src.interfaces.trainers import ICartographerTrainer
from src.models.sinkhorn_cross_attention import SinkhornCrossAttention


class CartographerTrainer(ICartographerTrainer):
    """
    Dedicated training routine and optimizer for Sinkhorn Cross-Attention graph matchers.
    """

    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 1e-3,
        device: Optional[torch.device] = None,
        loss_fn: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None,
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.loss_fn = loss_fn or SinkhornCrossAttention.alignment_loss
        self.model.to(self.device)

        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scaler = GradScaler(device=self.device.type if self.device.type in ('cuda', 'cpu') else 'cpu')

    def to(self, device: Any) -> 'CartographerTrainer':
        """Transfers the model and scaler to the target device."""
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler(device=self.device.type if self.device.type in ('cuda', 'cpu') else 'cpu')
        return self

    def train_step(
        self,
        source_data: Any,
        mutant_data: Any = None,
        ground_truth: Optional[torch.Tensor] = None
    ) -> float:
        """
        Executes a single forward + backward training step with mixed precision.

        Args:
            source_data: PyG Data representing source line graph, or tuple/list (source, mutant, ground_truth).
            mutant_data: PyG Data representing mutant line graph (optional if packed in source_data).
            ground_truth: [N_source, N_mutant] ground truth permutation matrix (optional if packed in source_data).

        Returns:
            Computed scalar loss value.
        """
        if mutant_data is None and isinstance(source_data, (tuple, list)) and len(source_data) >= 3:
            source_data, mutant_data, ground_truth = source_data[0], source_data[1], source_data[2]

        if mutant_data is None or ground_truth is None:
            raise ValueError("CartographerTrainer.train_step requires source_data, mutant_data, and ground_truth.")

        self.model.train()

        source_data = source_data.to(self.device)
        mutant_data = mutant_data.to(self.device)
        ground_truth = ground_truth.to(self.device)

        self.optimizer.zero_grad()

        with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
            predicted = self.model(source_data, mutant_data)
            loss = self.loss_fn(predicted, ground_truth)

        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()

