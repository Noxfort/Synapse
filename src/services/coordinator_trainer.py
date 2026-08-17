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
# File: src/services/coordinator_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Optional
from torch.amp import autocast, GradScaler


class CoordinatorTrainer:
    """
    Dedicated Training Routine & Optimizer for SpatialGAT Graph Models.
    """

    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 0.001,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scaler = GradScaler(device='cuda' if torch.cuda.is_available() else 'cpu')
        self.criterion = nn.MSELoss()

    def to(self, device: Any) -> 'CoordinatorTrainer':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler(device='cuda' if self.device.type == 'cuda' else 'cpu')
        return self

    def train_step(self, batch_data: Any) -> float:
        """
        Training step for Graph Data.
        """
        self.model.train()

        if hasattr(batch_data, 'x') and hasattr(batch_data, 'edge_index'):
            x = batch_data.x.to(self.device)
            edge_index = batch_data.edge_index.to(self.device)
            y = batch_data.y.to(self.device) if hasattr(batch_data, 'y') else x
        elif isinstance(batch_data, (tuple, list)):
            x, edge_index, y = batch_data
            x, edge_index, y = x.to(self.device), edge_index.to(self.device), y.to(self.device)
        else:
            return 0.0

        self.optimizer.zero_grad()

        with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
            out = self.model(x, edge_index)
            if isinstance(out, tuple):
                out = out[0]
            loss = self.criterion(out, y)

        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()
