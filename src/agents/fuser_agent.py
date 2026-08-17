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
# File: src/agents/fuser_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import numpy as np
import torch
from typing import Dict, Any, Optional, Union

# Base Agent and Contracts
from src.agents.base_agent import BaseAgent
from src.domain.interfaces import ISensorCalibrator, IFusionPipeline
from src.services.dynamic_sensor_calibrator import DynamicSensorCalibrator
from src.factories.fuser_model_factory import FuserModelFactory


class FuserAgent(BaseAgent):
    """
    The Fuser Agent ('O Sintetizador Global').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: Coordinates high-level perception inference.
    - Delegations:
      -> Neural GPU/Tensor Execution: IFusionPipeline (src/services/fusion_pipeline.py)
      -> Dynamic Sensor Calibration: ISensorCalibrator (src/services/dynamic_sensor_calibrator.py)
    """

    def __init__(
        self,
        pipeline: Optional[IFusionPipeline] = None,
        calibrator: Optional[ISensorCalibrator] = None,
        num_variates: int = 10,
        seq_len: int = 60,
        pred_len: int = 1,
        d_model: int = 64,
        n_heads: int = 4,
        layers: int = 2,
        spatial_dim: int = 32,
        name: str = "FuserAgent",
        **kwargs: Any
    ):
        """
        Initializes the Pure Fuser Orchestrator with injected services.
        """
        # Resolve Pipeline via Factory if not directly provided (DIP & Backward Compatibility)
        if pipeline is None:
            pipeline = FuserModelFactory.create_fusion_pipeline(
                num_variates=num_variates,
                seq_len=seq_len,
                pred_len=pred_len,
                d_model=d_model,
                n_heads=n_heads,
                layers=layers,
                spatial_dim=spatial_dim
            )

        super().__init__(model=getattr(pipeline, "module_dict", None), name=name)

        self.pipeline: IFusionPipeline = pipeline
        self.calibrator: ISensorCalibrator = calibrator or DynamicSensorCalibrator(num_variates=num_variates)
        self.cached_edge_index: Optional[torch.Tensor] = None

    def set_topology(self, edge_index: torch.Tensor):
        """Registers active map topology in the orchestrator."""
        self.cached_edge_index = edge_index

    def update_observability(self, active_mask: np.ndarray):
        """Delegates sensor observability state updates to the Calibrator service."""
        self.calibrator.update_observability(active_mask)

    def inference(self, input_data: Dict[str, Any]) -> np.ndarray:
        """Unified inference entry point."""
        if "x_temporal" not in input_data:
            raise ValueError("Fuser inference requires 'x_temporal'.")

        return self.fuse_state(
            current_history=input_data["x_temporal"],
            spatial_context=input_data.get("spatial_context"),
            observability_mask=input_data.get("observability_mask"),
            global_velocities=input_data.get("global_velocities"),
            edge_index=input_data.get("edge_index", self.cached_edge_index)
        )

    def fuse_state(
        self,
        current_history: Union[np.ndarray, torch.Tensor],
        spatial_context: Optional[torch.Tensor] = None,
        observability_mask: Optional[Any] = None,
        global_velocities: Optional[Any] = None,
        edge_index: Optional[torch.Tensor] = None
    ) -> np.ndarray:
        """
        Pure Orchestration Workflow:
        1. Executes neural execution pipeline service (Diffusion -> PINN -> iTransformer).
        2. Applies dynamic bias calibration on ground truth sensors.
        """
        # Step 1: Execute neural pipeline service (GPU tensor processing)
        raw_state = self.pipeline.execute(
            current_history=current_history,
            spatial_context=spatial_context,
            observability_mask=observability_mask,
            global_velocities=global_velocities,
            edge_index=edge_index if edge_index is not None else self.cached_edge_index
        )

        # Step 2: Apply dynamic sensor calibration
        return self.calibrator.apply(
            raw_output=raw_state,
            current_history=current_history,
            observability_mask=observability_mask
        )

    def predict_state(
        self,
        current_history: np.ndarray,
        spatial_context: Optional[torch.Tensor] = None
    ) -> np.ndarray:
        """Alias for backward compatibility with CycleProcessor."""
        return self.fuse_state(current_history, spatial_context=spatial_context)

    def train_step(self, batch_data: Any) -> float:
        """Interface compliance method (training lifecycle is encapsulated by FuserTrainer)."""
        return 0.0