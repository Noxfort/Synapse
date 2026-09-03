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
# File: src/physics/traffic_loss.py
# Author: Gabriel Moraes
# Date: 2026-08-20

from typing import Dict, Optional
import torch
import torch.nn as nn
from src.interfaces.physics import IPhysicsLossEngine
from src.physics.kinematics import (
    NonNegativityBoundsConstraint,
    KinematicAccelerationConstraint,
    TemporalSmoothnessConstraint,
)
from src.physics.continuum import ContinuumConservation, SpatialGraphConservation


class TrafficPhysicsLoss(nn.Module):
    """
    Unified Physics-Informed Neural Network (PINN) Loss Aggregator.
    
    Composes individual physical laws via Dependency Injection (DIP/OCP)
    and supports structural modality conditioning (Vehicle Count vs Speed vs Flow):
    1. Bounds (Non-negativity: q >= 0, v >= 0, rho >= 0, N >= 0)
    2. Kinematics (Acceleration bound: |dv/dt| <= a_max)
    3. Smoothness (Suppresses high-frequency sensor noise)
    4. Continuum Conservation (LWR relationship: q = rho * v)
    5. Spatial Conservation (Graph edge divergence)
    """

    def __init__(
        self,
        max_acceleration: float = 10.0,
        w_bounds: float = 1.0,
        w_kinematics: float = 0.5,
        w_smooth: float = 0.1,
        w_conservation: float = 0.5,
        w_spatial: float = 0.1,
        dt: float = 1.0,
        bounds_constraint: Optional[NonNegativityBoundsConstraint] = None,
        kinematics_constraint: Optional[KinematicAccelerationConstraint] = None,
        smoothness_constraint: Optional[TemporalSmoothnessConstraint] = None,
        continuum_constraint: Optional[ContinuumConservation] = None,
        spatial_constraint: Optional[SpatialGraphConservation] = None,
    ):
        super().__init__()
        
        self.w_bounds = w_bounds
        self.w_kinematics = w_kinematics
        self.w_smooth = w_smooth
        self.w_conservation = w_conservation
        self.w_spatial = w_spatial
        
        # Inject or instantiate sub-constraints
        self.bounds_constraint = bounds_constraint or NonNegativityBoundsConstraint()
        self.kinematics_constraint = kinematics_constraint or KinematicAccelerationConstraint(
            max_acceleration=max_acceleration, dt=dt
        )
        self.smoothness_constraint = smoothness_constraint or TemporalSmoothnessConstraint()
        self.continuum_constraint = continuum_constraint or ContinuumConservation()
        self.spatial_constraint = spatial_constraint or SpatialGraphConservation()

    def compute_losses(
        self,
        reconstruction: torch.Tensor,
        orig_x: Optional[torch.Tensor] = None,
        edge_index: Optional[torch.Tensor] = None,
        semantic_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, torch.Tensor]:
        """
        Computes physics residuals conditioned on the semantic modality of the sensor.
        
        Args:
            reconstruction: Tensor [Batch, SeqLen], [Batch, Channels, SeqLen], or [Batch, Nodes, Channels]
            orig_x: Optional ground-truth tensor
            edge_index: Optional graph connectivity [2, Num_Edges]
            semantic_type: Modality identified by Linguist ("Vehicle Count", "Vehicle Speed", "Traffic Flow", etc.)
            
        Returns:
            Dictionary with individual components and 'total_physics_loss'.
        """
        device = reconstruction.device
        sem = (semantic_type or "").lower()
        
        # 1. Non-negativity Bounds (Universal across all physical traffic quantities)
        loss_bounds = self.bounds_constraint.compute_residual(reconstruction)
        
        # 2. Kinematics & Temporal Smoothness
        loss_kinematics = self.kinematics_constraint.compute_residual(reconstruction)
        loss_smooth = self.smoothness_constraint.compute_residual(reconstruction)
        
        # 3. Continuum Conservation (q = rho * v) - Only for fluid/multivariate regimes
        if "count" in sem:
            # Discrete counts do not follow macroscopic continuous product laws
            loss_conservation = torch.tensor(0.0, device=device)
            w_kin = 0.1
            w_cons = 0.0
        elif "speed" in sem:
            loss_conservation = torch.tensor(0.0, device=device)
            w_kin = self.w_kinematics
            w_cons = 0.0
        else:
            if reconstruction.dim() == 3 and reconstruction.shape[1] >= 3:
                q = reconstruction[:, 0, :]
                v = reconstruction[:, 1, :]
                rho = reconstruction[:, 2, :]
                loss_conservation = self.continuum_constraint.compute_residual(q=q, v=v, rho=rho)
            elif reconstruction.dim() == 3 and reconstruction.shape[-1] >= 3:
                q = reconstruction[:, :, 0]
                v = reconstruction[:, :, 1]
                rho = reconstruction[:, :, 2]
                loss_conservation = self.continuum_constraint.compute_residual(q=q, v=v, rho=rho)
            else:
                loss_conservation = torch.tensor(0.0, device=device)
            w_kin = self.w_kinematics
            w_cons = self.w_conservation
            
        # 4. Spatial Conservation in Graphs
        if edge_index is not None and edge_index.numel() > 0 and reconstruction.dim() == 3:
            flow = reconstruction[:, :, 0:1] if reconstruction.shape[-1] >= 3 else reconstruction
            loss_spatial = self.spatial_constraint.compute_residual(flow=flow, edge_index=edge_index)
        else:
            loss_spatial = torch.tensor(0.0, device=device)
            
        # Total Weighted PINN Loss Conditioned on Modality
        total_physics = (
            self.w_bounds * loss_bounds +
            w_kin * loss_kinematics +
            self.w_smooth * loss_smooth +
            w_cons * loss_conservation +
            self.w_spatial * loss_spatial
        )
        
        return {
            "loss_bounds": loss_bounds,
            "loss_kinematics": loss_kinematics,
            "loss_smooth": loss_smooth,
            "loss_conservation": loss_conservation,
            "loss_spatial": loss_spatial,
            "total_physics_loss": total_physics
        }
