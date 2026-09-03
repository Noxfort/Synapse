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
# File: src/utils/normalization.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import torch
import numpy as np
from typing import Tuple


class TensorNormalizer:
    """
    Single Responsibility: Signal normalization for neural network inputs.
    
    Provides both Instance Normalization and Z-Score Normalization
    as reusable utilities, preventing code duplication across agents.
    """

    EPS = 1e-5

    @staticmethod
    def instance_norm(x: torch.Tensor, seq_dim: int = 1) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Instance Normalization: normalizes each sample independently along the sequence.
        Used by AuditorAgent (WaveletAEOCC).
        
        Args:
            x: Input tensor, e.g., [Batch, length, features] -> seq_dim=1
            seq_dim: The sequence (time) dimension over which to compute statistics.
            
        Returns:
            Tuple of (normalized_x, mean, std) for reversal.
        """
        mean = x.mean(dim=seq_dim, keepdim=True)
        std = x.std(dim=seq_dim, keepdim=True, unbiased=False)
        normalized = (x - mean) / (std + TensorNormalizer.EPS)
        return normalized, mean, std

    @staticmethod
    def instance_denorm(x_norm: torch.Tensor, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
        """Reverses instance normalization."""
        return (x_norm * (std + TensorNormalizer.EPS)) + mean

    @staticmethod
    def zscore_norm(x: torch.Tensor, seq_dim: int = -1) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Z-Score Normalization: normalizes along the sequence dimension independently per feature.
        This explicitly stops variables like Speed and Flow from being cross-contaminated.
        
        Args:
            x: Input tensor (e.g. [Batch, Channels, Length] -> seq_dim=2)
            seq_dim: The temporal dimension.
            
        Returns:
            Tuple of (normalized_x, mean, std) for reversal.
        """
        mean = x.mean(dim=seq_dim, keepdim=True)
        std = x.std(dim=seq_dim, keepdim=True, unbiased=False)
        normalized = (x - mean) / (std + TensorNormalizer.EPS)
        return normalized, mean, std

    @staticmethod
    def zscore_denorm(x_norm: torch.Tensor, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
        """Reverses Z-Score normalization."""
        return (x_norm * (std + TensorNormalizer.EPS)) + mean

    @staticmethod
    def sanitize(x: torch.Tensor) -> torch.Tensor:
        """Replaces NaN/Inf values with safe defaults."""
        if torch.isnan(x).any() or torch.isinf(x).any():
            return torch.nan_to_num(x, nan=0.0, posinf=1.0, neginf=-1.0)
        return x
