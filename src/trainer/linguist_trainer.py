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
# File: src/trainer/linguist_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-20

import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Any, Optional
from transformers import AutoTokenizer
from torch.amp import autocast, GradScaler

from src.interfaces.trainers import ILinguistTrainer
from src.models.neuro_symbolic import NeuroSymbolicModel
from src.utils.model_paths import get_distilroberta_base_path


class LinguistTrainer(ILinguistTrainer):
    """
    Dedicated Training Routine & Optimizer for NeuroSymbolic Reasoner Models.
    Optimizes the TCN-AE Autoencoder and Modality-Aware Physics Head with local convergence loops.
    """

    def __init__(
        self,
        model: NeuroSymbolicModel,
        tokenizer: Optional[AutoTokenizer] = None,
        model_name: Optional[str] = None,
        learning_rate: float = 1e-3,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        resolved_name = model_name or get_distilroberta_base_path()
        self.model_name = resolved_name
        if tokenizer is not None:
            self.tokenizer = tokenizer
        else:
            is_local = os.path.isdir(resolved_name)
            self.tokenizer = AutoTokenizer.from_pretrained(resolved_name, local_files_only=is_local)
        self.optimizer = optim.Adam(self.model.ae.parameters(), lr=learning_rate)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))
        self.criterion = nn.MSELoss()

    def to(self, device: Any) -> 'LinguistTrainer':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))
        return self

    def train_step(
        self,
        batch_data: Any,
        epochs: int = 10,
        semantic_type: Optional[str] = None
    ) -> float:
        """
        Optimizes the TCN-PINN Reasoner across local calibration epochs to achieve stable convergence.
        
        Args:
            batch_data: Numerical values or text representations of the signal.
            epochs: Number of local calibration iterations on the sample buffer (default 10).
            semantic_type: Modality identified by Linguist ("Vehicle Count", "Vehicle Speed", etc.).
            
        Returns:
            float: Final converged total loss (Reconstruction MSE + Physics Residual).
        """
        self.model.train()

        if isinstance(batch_data, (np.ndarray, torch.Tensor)):
            batch_size = batch_data.shape[0] if len(batch_data.shape) > 0 else 16
            texts = [f"Traffic stream {semantic_type or 'signal'}: {batch_data.tolist()[:10]}"] * batch_size
        elif isinstance(batch_data, list) and len(batch_data) > 0 and isinstance(batch_data[0], str):
            texts = batch_data
        elif isinstance(batch_data, list) and len(batch_data) > 0 and isinstance(batch_data[0], (int, float)):
            texts = [f"Traffic stream {semantic_type or 'signal'} series: {batch_data}"]
        elif isinstance(batch_data, dict) and "text" in batch_data:
            texts = batch_data["text"]
            if isinstance(texts, str):
                texts = [texts]
        else:
            texts = [f"Traffic sensor stream modality: {semantic_type or 'General'}"]

        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128
        )

        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        final_loss = 1.0

        for _ in range(max(1, epochs)):
            self.optimizer.zero_grad()

            with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                reconstruction, original, physics_residuals = self.model(
                    input_ids,
                    attention_mask,
                    semantic_type=semantic_type
                )
                loss_recon = self.criterion(reconstruction, original)
                loss_physics = physics_residuals.get("total_physics_loss", torch.tensor(0.0, device=self.device))
                loss_total = loss_recon + loss_physics

            if not torch.isfinite(loss_total):
                self.scaler.update()
                return 1e6

            self.scaler.scale(loss_total).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.ae.parameters(), max_norm=1.0)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            final_loss = loss_total.item()

        return final_loss
