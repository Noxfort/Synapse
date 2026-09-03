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
# File: src/physics/fundamental_diagrams.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
from src.interfaces.physics import IFundamentalDiagram


class GreenshieldsDiagram(nn.Module):
    """
    Standard Greenshields linear speed-density and parabolic flow-density relationship:
        v(k) = v_free * max(0, 1 - k / k_jam)
        q(k) = k * v(k) = k * v_free * (1 - k / k_jam)
    """

    def __init__(self, eps: float = 1e-6):
        super().__init__()
        self.eps = eps

    def compute_speed(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        """Computes speed v according to Greenshields model."""
        k_norm = torch.clamp(density / (k_jam + self.eps), min=0.0, max=1.0)
        v_theory = v_free * (1.0 - k_norm)
        return torch.clamp(v_theory, min=0.0)

    def compute_flow(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        """Computes flow q = k * v."""
        v_theory = self.compute_speed(density, v_free, k_jam)
        q_theory = torch.clamp(density, min=0.0) * v_theory
        return q_theory


class UnderwoodDiagram(nn.Module):
    """
    Underwood exponential speed-density model:
        v(k) = v_free * exp(-k / k_crit)
        q(k) = k * v_free * exp(-k / k_crit)
    """

    def __init__(self, eps: float = 1e-6):
        super().__init__()
        self.eps = eps

    def compute_speed(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        # k_crit is typically ~ k_jam / e or k_jam / 2
        k_crit = k_jam * 0.4 + self.eps
        k_pos = torch.clamp(density, min=0.0)
        v_theory = v_free * torch.exp(-k_pos / k_crit)
        return torch.clamp(v_theory, min=0.0)

    def compute_flow(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        v_theory = self.compute_speed(density, v_free, k_jam)
        return torch.clamp(density, min=0.0) * v_theory


class NewellDaganzoDiagram(nn.Module):
    """
    Simplified triangular / piecewise linear fundamental diagram (Newell-Daganzo):
        q = min(v_free * k, w * (k_jam - k))
    """

    def __init__(self, wave_speed_factor: float = 0.3, eps: float = 1e-6):
        super().__init__()
        self.wave_speed_factor = wave_speed_factor
        self.eps = eps

    def compute_speed(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        q_theory = self.compute_flow(density, v_free, k_jam)
        k_safe = torch.clamp(density, min=self.eps)
        return torch.clamp(q_theory / k_safe, min=0.0, max=v_free.max().item() if isinstance(v_free, torch.Tensor) and v_free.numel() > 0 else 120.0)

    def compute_flow(
        self,
        density: torch.Tensor,
        v_free: torch.Tensor,
        k_jam: torch.Tensor
    ) -> torch.Tensor:
        k_pos = torch.clamp(density, min=0.0)
        w = v_free * self.wave_speed_factor  # Congestion backward wave speed
        free_flow = v_free * k_pos
        congested_flow = torch.clamp(w * (k_jam - k_pos), min=0.0)
        return torch.minimum(free_flow, congested_flow)
