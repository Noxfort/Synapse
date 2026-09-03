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
# File: src/interfaces/pipelines.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from src.interfaces.base import IDeviceMovable


@runtime_checkable
class IPipeline(Protocol):
    """Contract for data ingestion pipelines."""
    def process_packet(self, source_id: str, payload: Any) -> bool: ...
    def is_ready_for_linguist(self, source_id: str) -> bool: ...


@runtime_checkable
class IFusionPipeline(IDeviceMovable, Protocol):
    """Contract for multi-model neural fusion pipelines."""
    def execute(
        self,
        current_history: Any,
        spatial_context: Optional[Any] = None,
        observability_mask: Optional[Any] = None,
        global_velocities: Optional[Any] = None,
        edge_index: Optional[Any] = None
    ) -> Any: ...

    def execute_operator(
        self,
        current_history: Any,
        query_coords: Optional[Any] = None,
        return_physics_residual: bool = False
    ) -> Any: ...


@runtime_checkable
class IAuditorPipeline(IDeviceMovable, Protocol):
    """Contract for anomaly detection and physical-spectral auditing pipeline."""
    def audit(self, input_data: Any) -> Dict[str, Any]: ...


@runtime_checkable
class IImputerPipeline(IDeviceMovable, Protocol):
    """Contract for missing sensor data reconstruction and gap imputation."""
    def reconstruct(self, incomplete_seq: Any, chunk_size: int = 4096) -> Any: ...


@runtime_checkable
class ICorrectorPipeline(IDeviceMovable, Protocol):
    """Contract for physics-informed denoising and golden dataset reconstruction."""
    def correct(self, input_data: Any, batch_size: int = 128) -> Any: ...


@runtime_checkable
class ISpecialistPipeline(IDeviceMovable, Protocol):
    """Contract for temporal convolutional feature extraction and decoding."""
    def predict(self, input_sequence: Any) -> Any: ...


@runtime_checkable
class ILinguistPipeline(IDeviceMovable, Protocol):
    """Contract for semantic-physical validation and contradiction detection."""
    def validate(self, input_data: Any) -> Dict[str, Any]: ...
    def calibrate_threshold(self, validation_texts: List[str]) -> None: ...


@runtime_checkable
class ICoordinatorPipeline(IDeviceMovable, Protocol):
    """Contract for spatial graph reasoning and global network embeddings."""
    def forward_pass(self, x: Any, edge_index: Optional[Any] = None) -> Any: ...


@runtime_checkable
class IJuristPipeline(IDeviceMovable, Protocol):
    """Contract for legal-technical traffic reasoning and on-demand SLM pipeline."""
    @property
    def is_loaded(self) -> bool: ...
    def generate(self, context_data: Dict[str, Any], auto_unload: bool = False) -> str: ...
    def generate_report(
        self,
        tensor_data: Dict[str, Any],
        timestamp: str = "",
        locale: str = "pt_BR",
        target: str = "XAI_Attribution",
        auto_unload: bool = True,
        **kwargs: Any
    ) -> str: ...
    def load_resources(self, device: str = "auto", gpu_layers: int = 16) -> None: ...
    def unload_resources(self) -> None: ...

