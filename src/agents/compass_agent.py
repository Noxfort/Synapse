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
# File: src/agents/compass_agent.py
# Author: Gabriel Moraes
# Date: 2026-09-05

import logging
from typing import Dict, Any, List, Optional
import numpy as np

from src.agents.base_agent import BaseAgent
from src.domain.entities import MapEdge, DataSource
from src.interfaces.pipelines import ICompassPipeline
from src.pipeline.compass_pipeline import CompassPipeline

logger = logging.getLogger("Synapse.Agents.Compass")


class CompassAgent(BaseAgent):
    """
    The Compass Agent ('A Bússola').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - [SRP] Single Responsibility: Reconciles sensor orientation and directional alignment in two-way streets.
    - [DIP] Relies on ICompassPipeline protocol for neural and geometric disambiguation.
    - [LSP] Conforms to BaseAgent interface for unified device management and lifecycle.
    """

    def __init__(
        self,
        pipeline: Optional[ICompassPipeline] = None,
        model_name: Optional[str] = None,
        name: str = "CompassAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = CompassPipeline(model_name=model_name)

        model = getattr(pipeline, "transformer", None)
        super().__init__(model=model, name=name)

        self.pipeline: ICompassPipeline = pipeline

    def inference(self, input_data: Any) -> Dict[str, Any]:
        """
        Unified BaseAgent inference contract.
        Expects dict with 'source', 'candidate_edges', and optional 'data_chunk', 'data_np', 'semantic_type'.
        """
        if isinstance(input_data, dict):
            return self.orient_and_reconcile(
                source=input_data.get("source"),
                candidate_edges=input_data.get("candidate_edges", []),
                data_chunk=input_data.get("data_chunk"),
                data_np=input_data.get("data_np"),
                semantic_type=input_data.get("semantic_type")
            )
        return {
            "orientation": "INDETERMINADO",
            "primary_edge_id": None,
            "confidence": 0.0,
            "method": "invalid_input"
        }

    def orient_and_reconcile(
        self,
        source: DataSource,
        candidate_edges: List[MapEdge],
        data_chunk: Optional[List[Any]] = None,
        data_np: Optional[np.ndarray] = None,
        semantic_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delegates directional reconciliation to the CompassPipeline.
        """
        if hasattr(self.pipeline, "orient_and_reconcile"):
            return self.pipeline.orient_and_reconcile(
                source=source,
                candidate_edges=candidate_edges,
                data_chunk=data_chunk,
                data_np=data_np,
                semantic_type=semantic_type
            )
        return {
            "orientation": "INDETERMINADO",
            "primary_edge_id": None,
            "confidence": 0.0,
            "method": "pipeline_missing"
        }
