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
# File: src/services/dynamic_sensor_calibrator.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import numpy as np
import torch
from typing import Optional, Any
from src.interfaces.providers import ISensorCalibrator


class DynamicSensorCalibrator(ISensorCalibrator):
    """
    Service responsible for dynamic sensor calibration and online bias correction.
    
    Adheres to Single Responsibility Principle (SRP):
    - Tracks active observability states across physical nodes.
    - Dynamically adapts Fast Bias Exponential Moving Average (EMA).
    - Compensates residual discrepancies between Ground Truth sensors and predicted states.
    """

    def __init__(
        self,
        num_variates: int,
        initial_alpha: float = 0.05,
        max_alpha: float = 0.2
    ):
        """
        Args:
            num_variates: Number of physical variates / traffic nodes.
            initial_alpha: Base smoothing factor for EMA.
            max_alpha: Maximum adaptive alpha during rapid sensor onboarding.
        """
        self.num_variates = num_variates
        self.base_alpha = initial_alpha
        self.max_alpha = max_alpha
        self.ema_alpha = initial_alpha
        self.ema_bias = np.zeros(num_variates, dtype=np.float32)
        self.calibration_cycles = 0

    def update_observability(self, active_mask: np.ndarray):
        """
        Signals dynamic calibration when new sensors come online.
        Increases adaptation rate proportionally to active sensors.
        """
        active_count = int(np.sum(active_mask))
        self.calibration_cycles += 1
        # Dynamic EMA adaptation rate: faster when new sensors enter
        self.ema_alpha = min(self.max_alpha, self.base_alpha + 0.01 * active_count)

    def apply(
        self,
        raw_output: np.ndarray,
        current_history: Any,
        observability_mask: Optional[Any] = None
    ) -> np.ndarray:
        """
        Computes residual error on active Ground Truth sensors and applies calibration bias.
        
        Args:
            raw_output: [Num_Variates] state vector output from the neural pipeline.
            current_history: Temporal history array or tensor.
            observability_mask: Binary mask where 1 indicates active ground truth sensor.
            
        Returns:
            calibrated_vector: [Num_Variates] refined and bias-corrected vector.
        """
        if observability_mask is None:
            return raw_output + self.ema_bias

        if isinstance(observability_mask, torch.Tensor):
            mask_np = observability_mask.detach().cpu().numpy().flatten()
        elif isinstance(observability_mask, np.ndarray):
            mask_np = observability_mask.flatten()
        else:
            mask_np = np.array(observability_mask, dtype=np.float32).flatten()

        active_idx = np.where(mask_np > 0.5)[0]
        if len(active_idx) > 0:
            if isinstance(current_history, torch.Tensor):
                hist_np = current_history.detach().cpu().numpy()
            elif isinstance(current_history, np.ndarray):
                hist_np = current_history
            else:
                hist_np = np.array(current_history, dtype=np.float32)

            if hist_np.ndim >= 2:
                last_observed = hist_np[-1] if hist_np.ndim == 2 else hist_np[0, -1]
                error = last_observed[active_idx] - raw_output[active_idx]
                self.ema_bias[active_idx] = (
                    (1.0 - self.ema_alpha) * self.ema_bias[active_idx]
                    + self.ema_alpha * error
                )

        return raw_output + self.ema_bias

    def reset(self):
        """Resets calibration state to zero bias."""
        self.ema_bias.fill(0.0)
        self.ema_alpha = self.base_alpha
        self.calibration_cycles = 0
