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
# File: src/strategies/deep_svdd_calibrator.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
from typing import Tuple, Optional


class DeepSVDDCalibrator:
    """
    Statistical Deep SVDD (Support Vector Data Description) Calibrator.
    
    Decoupled strategy for:
    1. Hypersphere Center Initialization (c = mean of initial baseline representations).
    2. Adaptive Anomaly Threshold Tracking via Exponential Moving Average (EMA).
    3. Anomaly Score Computation: ||z - c||^2.
    """

    def __init__(self, latent_dim: int, initial_threshold: float = 0.5, momentum: float = 0.1):
        self.latent_dim = latent_dim
        self.momentum = momentum
        self.center: Optional[torch.Tensor] = None
        self.threshold: float = initial_threshold
        self.center_initialized: bool = False

    def init_center(self, z: torch.Tensor) -> torch.Tensor:
        """
        Initializes the hypersphere center 'c' as the mean of baseline latent vectors.
        """
        with torch.no_grad():
            self.center = torch.mean(z, dim=0, keepdim=True).detach()
            self.center_initialized = True
            return self.center

    def update_threshold(self, anomaly_scores: torch.Tensor) -> float:
        """
        Updates the anomaly threshold based on the statistics of current batch (mean + 2*std).
        """
        with torch.no_grad():
            std_val = anomaly_scores.std().item() if anomaly_scores.numel() > 1 else 0.0
            mean_val = anomaly_scores.mean().item()
            current_limit = mean_val + 2.0 * std_val
            self.threshold = (1.0 - self.momentum) * self.threshold + self.momentum * current_limit
            return self.threshold

    def compute_anomaly_scores(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes Deep SVDD anomaly score: ||z - center||^2 and binary classification mask.
        
        Args:
            z: Latent representations [Batch, LatentDim]
        Returns:
            scores: Euclidean distances to center [Batch]
            is_anomaly: Boolean tensor indicating if score exceeds adaptive threshold [Batch]
        """
        if not self.center_initialized or self.center is None:
            self.init_center(z)
            
        center = self.center.to(z.device)
        scores = torch.sum((z - center) ** 2, dim=-1)
        is_anomaly = scores > self.threshold
        return scores, is_anomaly
