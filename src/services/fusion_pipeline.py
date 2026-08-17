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
# File: src/services/fusion_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Any, Union
from torch.amp import autocast
from src.domain.interfaces import IFusionPipeline


class FusionPipeline(IFusionPipeline):
    """
    Service responsible for GPU tensor processing and multi-model execution.
    
    Adheres to Single Responsibility Principle (SRP):
    - Encapsulates low-level PyTorch tensor conversions and memory management.
    - Chains the execution: DiffusionGATv2 -> PINNTrafficFlow -> iTransformer.
    - Frees the FuserAgent orchestrator from dealing with tensors and devices.
    """

    def __init__(
        self,
        diffusion_model: nn.Module,
        pinn_model: nn.Module,
        temporal_model: nn.Module,
        spatial_dim: int = 32
    ):
        self.diffusion = diffusion_model
        self.pinn = pinn_model
        self.temporal = temporal_model
        self.spatial_dim = spatial_dim

        # Bundle into ModuleDict for device and parameter tracking
        self.module_dict = nn.ModuleDict({
            "diffusion": self.diffusion,
            "pinn": self.pinn,
            "itransformer": self.temporal
        })

    def _get_current_device(self) -> torch.device:
        """Finds the current device of the underlying models."""
        try:
            return next(self.module_dict.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def to(self, device: torch.device) -> 'FusionPipeline':
        """Moves internal neural models to the specified compute device."""
        self.module_dict.to(device)
        return self

    def execute(
        self,
        current_history: Union[np.ndarray, torch.Tensor],
        spatial_context: Optional[torch.Tensor] = None,
        observability_mask: Optional[Any] = None,
        global_velocities: Optional[Any] = None,
        edge_index: Optional[torch.Tensor] = None
    ) -> np.ndarray:
        """
        Executes the forward neural fusion pass in eval mode with no gradients.
        
        Returns:
            raw_state: [Num_Variates] uncalibrated state vector at t=0.
        """
        self.module_dict.eval()
        device = self._get_current_device()

        with torch.no_grad():
            tensor_x = self._prepare_temporal_tensor(current_history, device)
            num_nodes = tensor_x.size(-1)

            cur_edge_index = self._resolve_edge_index(edge_index, device)
            mask_tensor = self._prepare_optional_tensor(observability_mask, device)
            g_vel_tensor = self._prepare_optional_tensor(global_velocities, device)
            spatial_feat = self._prepare_spatial_tensor(spatial_context, num_nodes, device)

            device_type = device.type if device.type != 'mps' else 'cpu'

            with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
                # Step 1: Graph Diffusion Extrapolation
                diffused_spatial, _ = self.diffusion(
                    x=spatial_feat,
                    edge_index=cur_edge_index,
                    observability_mask=mask_tensor,
                    global_speed_factor=g_vel_tensor
                )

                # Step 2: Physics-Informed Regularization (PINN)
                refined_spatial, _ = self.pinn(
                    x_embedding=diffused_spatial,
                    edge_index=cur_edge_index,
                    global_velocities=g_vel_tensor
                )

                # Step 3: Spatio-Temporal Cross-Attention
                refined_state = self.temporal(
                    tensor_x,
                    spatial_context=refined_spatial
                )

            return refined_state.cpu().float().numpy().flatten()

    def _prepare_temporal_tensor(self, current_history: Any, device: torch.device) -> torch.Tensor:
        if isinstance(current_history, torch.Tensor):
            t = current_history.to(device)
        elif isinstance(current_history, np.ndarray):
            t = torch.FloatTensor(current_history).to(device)
        else:
            t = torch.tensor(current_history, dtype=torch.float, device=device)
        if t.dim() == 2:
            t = t.unsqueeze(0)
        return t

    def _resolve_edge_index(self, edge_index: Optional[torch.Tensor], device: torch.device) -> torch.Tensor:
        if edge_index is None:
            return torch.empty((2, 0), dtype=torch.long, device=device)
        return edge_index.to(device)

    def _prepare_optional_tensor(self, data: Optional[Any], device: torch.device) -> Optional[torch.Tensor]:
        if data is None:
            return None
        if isinstance(data, torch.Tensor):
            return data.float().to(device)
        if isinstance(data, np.ndarray):
            return torch.from_numpy(data).float().to(device)
        return torch.tensor(data, dtype=torch.float, device=device)

    def _prepare_spatial_tensor(self, spatial_context: Optional[torch.Tensor], num_nodes: int, device: torch.device) -> torch.Tensor:
        if spatial_context is None:
            return torch.zeros((1, num_nodes, self.spatial_dim), device=device)
        feat = spatial_context.to(device)
        if feat.dim() == 2:
            feat = feat.unsqueeze(0)
        return feat
