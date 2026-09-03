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
# File: src/agents/coordinator_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import logging
from typing import Any, Optional, Dict

from src.agents.base_agent import BaseAgent
from src.interfaces.pipelines import ICoordinatorPipeline
from src.interfaces.trainers import ICoordinatorTrainer
from src.pipeline.coordinator_pipeline import CoordinatorPipeline
from src.trainer.coordinator_trainer import CoordinatorTrainer

logger = logging.getLogger("Synapse.CoordinatorAgent")


class CoordinatorAgent(BaseAgent):
    """
    The Coordinator Agent ('O Estrategista').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: Manages spatial reasoning across the graph topology.
    - Delegations:
      -> Spatial GAT Execution: ICoordinatorPipeline (src/pipeline/coordinator_pipeline.py)
      -> Graph Optimization Routines: ICoordinatorTrainer (src/trainer/coordinator_trainer.py)
    """

    def __init__(
        self,
        pipeline: Optional[ICoordinatorPipeline] = None,
        trainer: Optional[ICoordinatorTrainer] = None,
        in_channels: int = 32,
        hidden_channels: int = 32,
        out_channels: int = 32,
        heads: int = 2,
        dropout: float = 0.1,
        learning_rate: float = 0.001,
        name: str = "CoordinatorAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = CoordinatorPipeline(
                in_channels=in_channels,
                hidden_channels=hidden_channels,
                out_channels=out_channels,
                heads=heads,
                dropout=dropout
            )

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: ICoordinatorPipeline = pipeline
        self.trainer: ICoordinatorTrainer = trainer or CoordinatorTrainer(
            model=self.model,
            learning_rate=learning_rate,
            device=getattr(self.pipeline, "device", None)
        )

    @property
    def cached_edge_index(self) -> Optional[torch.Tensor]:
        return getattr(self.pipeline, "cached_edge_index", None)

    @cached_edge_index.setter
    def cached_edge_index(self, edge_index: Optional[torch.Tensor]):
        if hasattr(self.pipeline, "cached_edge_index"):
            self.pipeline.cached_edge_index = edge_index

    def set_topology(self, edge_index: torch.Tensor):
        """Injects topology context into the underlying pipeline memory."""
        self.pipeline.set_topology(edge_index)

    def inference(self, input_data: Dict[str, Any]) -> Any:
        """Unified inference entry point for graph spatial reasoning."""
        x = input_data.get("x_spatial")
        edge_index = input_data.get("edge_index")

        if x is None:
            raise ValueError("Coordinator inference requires 'x_spatial'.")

        try:
            return self.forward_pass(x, edge_index)
        except Exception as e:
            logger.error(f"[Coordinator] Inference failed: {e}")
            return torch.zeros((1, 1))

    def forward_pass(self, x: torch.Tensor, edge_index: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Delegates spatial graph forward pass to CoordinatorPipeline."""
        return self.pipeline.forward_pass(x, edge_index)

    def train_step(self, batch_data: Any) -> float:
        """Delegates graph neural training to CoordinatorTrainer."""
        return self.trainer.train_step(batch_data)
