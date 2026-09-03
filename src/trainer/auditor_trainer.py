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
# File: src/trainer/auditor_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Union, Tuple, Optional
from torch.amp import autocast, GradScaler
import warnings

from src.interfaces.trainers import IAuditorTrainer
from src.models.wavelet_ae_occ import WaveletSpectralAE, WaveletAEOCC
from src.strategies.deep_svdd_calibrator import DeepSVDDCalibrator
from src.physics.traffic_loss import TrafficPhysicsLoss
from src.utils.normalization import TensorNormalizer


class AuditorTrainer(IAuditorTrainer):
    """
    Dedicated Training Routine & Optimizer for Auditor Neural Models.
    Manages AMP GradScaler, multi-objective losses, and adaptive threshold calibration.
    """

    def __init__(
        self,
        model: WaveletSpectralAE,
        calibrator: Optional[DeepSVDDCalibrator] = None,
        physics_engine: Optional[TrafficPhysicsLoss] = None,
        learning_rate: float = 1e-3,
        physics_weight: float = 0.5,
        max_acceleration: float = 10.0,
        enable_pinn: bool = True,
        device: Optional[torch.device] = None
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.physics_weight = physics_weight
        self.enable_pinn = enable_pinn
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.calibrator = calibrator or DeepSVDDCalibrator(latent_dim=getattr(model, "latent_dim", 16))
        self.physics_engine = physics_engine or TrafficPhysicsLoss(max_acceleration=max_acceleration)

        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        self.criterion_rec = nn.MSELoss()
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))

    def to(self, device: Any) -> 'AuditorTrainer':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.scaler = GradScaler('cuda' if self.device.type == 'cuda' else 'cpu', enabled=(self.device.type == 'cuda'))
        return self

    def train_step(self, input_data: Union[torch.Tensor, Tuple[torch.Tensor, Any]]) -> float:
        """
        Performs a single training step optimizing spectral, time, SVDD compactness, and PINN physics.
        """
        self.model.train()

        if isinstance(input_data, (tuple, list)):
            x = input_data[0]
        else:
            x = input_data

        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, dtype=torch.float32)

        x = x.to(self.device)
        if x.ndim == 1:
            x = x.unsqueeze(0)

        # Instance Normalization (SRP)
        x = TensorNormalizer.sanitize(x)
        x, _, _ = TensorNormalizer.instance_norm(x)
        x = TensorNormalizer.sanitize(x)

        self.optimizer.zero_grad()
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                feats, z, rec_feats, time_recon = self.model(x, return_time_recon=True)

            if not self.calibrator.center_initialized:
                self.calibrator.init_center(z)

            loss_rec = self.criterion_rec(rec_feats, feats)
            loss_time = self.criterion_rec(time_recon, x)
            
            center = self.calibrator.center.to(self.device)
            dist = torch.sum((z - center) ** 2, dim=1)
            loss_occ = torch.mean(dist)
            
            physics_res = self.physics_engine.compute_losses(time_recon, orig_x=x)
            loss_physics = physics_res["total_physics_loss"] if self.enable_pinn else torch.tensor(0.0, device=self.device)

            loss = loss_rec + (0.5 * loss_time) + (0.1 * loss_occ) + (self.physics_weight * loss_physics)

        if not torch.isfinite(loss):
            return 100.0

        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=0.5)
        self.scaler.step(self.optimizer)
        self.scaler.update()

        with torch.no_grad():
            rec_err = torch.mean((rec_feats - feats) ** 2, dim=1)
            time_err = torch.mean((time_recon - x) ** 2, dim=1)
            phys_val = physics_res["total_physics_loss"].detach() if self.enable_pinn else 0.0
            batch_scores = rec_err + (0.5 * time_err) + (0.1 * dist) + (self.physics_weight * phys_val)
            self.calibrator.update_threshold(batch_scores)

        return loss.item()
