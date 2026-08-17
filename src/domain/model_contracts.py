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
# File: src/domain/model_contracts.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Protocol, runtime_checkable, Any, Optional, Tuple, Dict, List
import torch

@runtime_checkable
class ITimeSeriesModel(Protocol):
    """Contract for pure time-series sequence models (imputation/forecasting/stress fusion)."""
    def forward(self, x: torch.Tensor, *args: Any, **kwargs: Any) -> torch.Tensor: ...

@runtime_checkable
class ITimeSeriesAutoencoder(Protocol):
    """Contract for deterministic or stochastic time-series autoencoders."""
    def forward(self, x: torch.Tensor, *args: Any, **kwargs: Any) -> Any: ...

@runtime_checkable
class IGraphAttentionModel(Protocol):
    """Contract for spatial or spatio-temporal graph attention networks."""
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, *args: Any, **kwargs: Any) -> Any: ...

@runtime_checkable
class IGraphMatcherModel(Protocol):
    """Contract for Siamese graph matching architectures."""
    def forward(self, source_data: Any, target_data: Any) -> torch.Tensor: ...

@runtime_checkable
class ISemanticEmbeddingModel(Protocol):
    """Contract for NLP embedding models extracting continuous representations."""
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor: ...
