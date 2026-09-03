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
# File: src/trainer/corrector_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
import logging
from typing import Dict, Optional, Any
from torch.amp import autocast, GradScaler

from src.interfaces.trainers import ICorrectorTrainer
from src.models.pi_vae_tcn import PIVAETCN
from src.utils.normalization import TensorNormalizer
from src.utils.convergence_tracker import MarginalConvergenceTracker

logger = logging.getLogger("Synapse.CorrectorTrainer")


class CorrectorTrainer(ICorrectorTrainer):
    """
    Dedicated Training Routine & Optimizer for Corrector PI-VAE-TCN Models.
    Manages physics-informed losses, KL divergence, and marginal convergence tracking.
    """

    def __init__(
        self,
        model: PIVAETCN,
        learning_rate: float = 1e-3,
        physics_weight: float = 0.1,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.physics_weight = physics_weight
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))

    def to(self, device: Any) -> 'CorrectorTrainer':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))
        return self

    def train_step(self, batch_data: Any) -> float:
        """
        Single training step with Z-Score normalization and PINN loss terms.
        """
        self.model.train()

        if not isinstance(batch_data, torch.Tensor):
            batch_data = torch.tensor(batch_data, dtype=torch.float32)

        if batch_data.dim() == 2:
            batch_data = batch_data.unsqueeze(1)
        elif batch_data.dim() == 3:
            batch_data = batch_data.permute(0, 2, 1)

        batch_data = batch_data.to(self.device)
        batch_data = TensorNormalizer.sanitize(batch_data)

        batch_data_norm, mean, std = TensorNormalizer.zscore_norm(batch_data, seq_dim=2)

        self.optimizer.zero_grad()
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
            recon_x_norm, mu, logvar = self.model(batch_data_norm)
            recon_loss = torch.nn.functional.mse_loss(recon_x_norm, batch_data_norm, reduction='mean')

            logvar_clamped = torch.clamp(logvar, min=-10.0, max=5.0)
            mu_clamped = torch.clamp(mu, min=-20.0, max=20.0)
            kl_div = -0.5 * torch.mean(1 + logvar_clamped - mu_clamped.pow(2) - logvar_clamped.exp())

            recon_x = TensorNormalizer.zscore_denorm(recon_x_norm.float(), mean, std)
            physics_residuals = self.model.compute_physics_residuals(recon_x, batch_data)
            physics_loss = physics_residuals.get("total_physics_loss", torch.tensor(0.0, device=self.device))

            beta = 0.001
            loss = recon_loss + (beta * kl_div) + (self.physics_weight * physics_loss)

        if not torch.isfinite(loss):
            logger.warning("[CorrectorTrainer] NaNs/Infs detected in loss computation. Skipping step.")
            self.scaler.update()
            return 1e6

        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=0.1)
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()

    def train(
        self,
        data: np.ndarray,
        epochs: int = 100,
        batch_size: int = 64,
        tracker: Optional[MarginalConvergenceTracker] = None,
        use_dynamic_convergence: bool = True
    ) -> Dict[str, list]:
        """
        Full training loop with dynamic marginal convergence tracking.
        """
        dataset_size = data.shape[0]
        history = {'loss': []}
        x_tensor_cpu = torch.tensor(data, dtype=torch.float32)

        if tracker is None and use_dynamic_convergence:
            tracker = MarginalConvergenceTracker(
                min_epochs=5,
                max_epochs=epochs,
                patience=4,
                min_delta=1e-4,
                restore_best_weights=True
            )

        max_loops = tracker.max_epochs if tracker else epochs

        for epoch in range(max_loops):
            epoch_loss = 0.0
            indices = torch.randperm(dataset_size)

            for i in range(0, dataset_size, batch_size):
                batch_indices = indices[i:i + batch_size]
                batch_x = x_tensor_cpu[batch_indices]

                step_loss = self.train_step(batch_x)
                if step_loss < 1e5:
                    epoch_loss += step_loss

                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()

            avg_loss = epoch_loss / max(1, (dataset_size // batch_size))
            history['loss'].append(avg_loss)

            if tracker and tracker.step(epoch, avg_loss, model=self.model):
                logger.info(f"[CorrectorTrainer] 🛑 Converged at epoch {epoch + 1} ({tracker.stop_reason}) | Best Loss: {tracker.best_loss:.4f}")
                break

        return history
