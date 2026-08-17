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
# File: src/services/coordinator_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import logging
from typing import Optional, Any
from torch.amp import autocast

try:
    from src.models.gatv2_lite import SpatialGAT
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False
    SpatialGAT = None

logger = logging.getLogger("Synapse.CoordinatorPipeline")


class CoordinatorPipeline:
    """
    Dedicated Neural Pipeline for Spatial Graph Reasoning (GATv2).
    Encapsulates topology context caching, node embedding transformations, and AMP forward passes.
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        in_channels: int = 32,
        hidden_channels: int = 32,
        out_channels: int = 32,
        heads: int = 2,
        dropout: float = 0.1,
        device: Optional[torch.device] = None,
        **kwargs: Any
    ):
        if not PYG_AVAILABLE or SpatialGAT is None:
            raise ImportError("CoordinatorPipeline requires 'torch_geometric' and 'SpatialGAT' to be available.")

        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if model is not None:
            self.model = model
        else:
            self.model = SpatialGAT(
                in_channels=in_channels,
                hidden_channels=hidden_channels,
                out_channels=out_channels,
                heads=heads,
                dropout=dropout
            )

        self.model.to(self.device)
        self.cached_edge_index: Optional[torch.Tensor] = None

    def to(self, device: Any) -> 'CoordinatorPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        if self.cached_edge_index is not None:
            self.cached_edge_index = self.cached_edge_index.to(self.device)
        return self

    def set_topology(self, edge_index: torch.Tensor):
        """
        Injects and caches graph topology in GPU memory.
        """
        self.cached_edge_index = edge_index.to(self.device)

    def forward_pass(self, x: torch.Tensor, edge_index: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Processes graph node features through SpatialGAT.
        """
        self.model.eval()
        x = x.to(self.device)

        current_edge_index = edge_index if edge_index is not None else self.cached_edge_index
        if current_edge_index is None:
            raise ValueError("[CoordinatorPipeline] Missing topology context. Provide edge_index or call set_topology().")

        current_edge_index = current_edge_index.to(self.device)

        with torch.no_grad():
            with autocast(device_type=self.device.type, enabled=(self.device.type == 'cuda')):
                out = self.model(x, current_edge_index)
                if isinstance(out, tuple):
                    return out[0]
                return out
