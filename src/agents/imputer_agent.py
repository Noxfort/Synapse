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
# File: src/agents/imputer_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import numpy as np
from typing import Any, Optional

from src.agents.base_agent import BaseAgent
from src.domain.interfaces import IImputerPipeline, IImputerTrainer
from src.services.imputer_pipeline import ImputerPipeline
from src.services.imputer_trainer import ImputerTrainer


class ImputerAgent(BaseAgent):
    """
    The Imputer Agent ('O Reconstrutor').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: Manages temporal gap-filling and data reconstruction.
    - Delegations:
      -> Chunked Sliding-Window Reconstruction: IImputerPipeline (src/services/imputer_pipeline.py)
      -> Masked Optimization Routine: IImputerTrainer (src/services/imputer_trainer.py)
    """

    def __init__(
        self,
        pipeline: Optional[IImputerPipeline] = None,
        trainer: Optional[IImputerTrainer] = None,
        feature_dim: int = 4,
        seq_len: int = 24,
        patch_len: int = 8,
        stride: int = 4,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 128,
        dropout: float = 0.1,
        learning_rate: float = 0.001,
        name: str = "ImputerAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = ImputerPipeline(
                feature_dim=feature_dim,
                seq_len=seq_len,
                patch_len=patch_len,
                stride=stride,
                d_model=d_model,
                n_heads=n_heads,
                n_layers=n_layers,
                d_ff=d_ff,
                dropout=dropout
            )

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: IImputerPipeline = pipeline
        self.trainer: IImputerTrainer = trainer or ImputerTrainer(
            model=self.model,
            learning_rate=learning_rate,
            device=getattr(self.pipeline, "device", None)
        )
        self.feature_dim = feature_dim
        self.seq_len = seq_len

    def inference(self, input_data: Any) -> Any:
        """Standard Interface: Reconstructs missing values."""
        return self.impute(input_data)

    def impute(self, incomplete_seq: np.ndarray, chunk_size: int = 4096) -> np.ndarray:
        """Delegates sequence reconstruction to ImputerPipeline."""
        return self.pipeline.reconstruct(incomplete_seq, chunk_size=chunk_size)

    def train_step(self, batch_data: Any) -> float:
        """Delegates masked training step to ImputerTrainer."""
        return self.trainer.train_step(batch_data)