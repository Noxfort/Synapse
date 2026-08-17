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
# File: src/agents/corrector_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import os
import numpy as np
from typing import Dict, Optional, Any

from src.agents.base_agent import BaseAgent
from src.domain.interfaces import ICorrectorPipeline, ICorrectorTrainer
from src.services.corrector_pipeline import CorrectorPipeline
from src.services.corrector_trainer import CorrectorTrainer
from src.utils.convergence_tracker import MarginalConvergenceTracker


class CorrectorAgent(BaseAgent):
    """
    The Corrector Agent (Zelador).
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: Manages physics-informed denoising and golden dataset generation.
    - Delegations:
      -> PI-VAE Inference & Normalization: ICorrectorPipeline (src/services/corrector_pipeline.py)
      -> PI-VAE Convergence & Training: ICorrectorTrainer (src/services/corrector_trainer.py)
    """

    def __init__(
        self,
        pipeline: Optional[ICorrectorPipeline] = None,
        trainer: Optional[ICorrectorTrainer] = None,
        input_dim: int = 1,
        seq_len: int = 10,
        hidden_dim: int = 64,
        latent_dim: int = 32,
        kernel_size: int = 3,
        learning_rate: float = 1e-3,
        physics_weight: float = 0.1,
        max_acceleration: float = 10.0,
        device: Optional[str] = None,
        name: str = "CorrectorAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = CorrectorPipeline(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                latent_dim=latent_dim,
                kernel_size=kernel_size,
                max_acceleration=max_acceleration,
                device=device
            )

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: ICorrectorPipeline = pipeline
        self.trainer: ICorrectorTrainer = trainer or CorrectorTrainer(
            model=self.model,
            learning_rate=learning_rate,
            physics_weight=physics_weight,
            device=getattr(self.pipeline, "device", None)
        )
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.kernel_size = kernel_size
        self.learning_rate = learning_rate
        self.physics_weight = physics_weight
        self.max_acceleration = max_acceleration

    def inference(self, input_data: Any, batch_size: int = 128) -> np.ndarray:
        """Delegates denoising and signal correction to CorrectorPipeline."""
        return self.pipeline.correct(input_data, batch_size=batch_size)

    def train_step(self, batch_data: Any) -> float:
        """Delegates single step optimization to CorrectorTrainer."""
        return self.trainer.train_step(batch_data)

    def train(
        self,
        data: np.ndarray,
        epochs: int = 100,
        batch_size: int = 64,
        tracker: Optional[MarginalConvergenceTracker] = None,
        use_dynamic_convergence: bool = True
    ) -> Dict[str, list]:
        """Delegates full convergence training to CorrectorTrainer."""
        return self.trainer.train(
            data=data,
            epochs=epochs,
            batch_size=batch_size,
            tracker=tracker,
            use_dynamic_convergence=use_dynamic_convergence
        )

    def save_weights(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        super().save_weights(path)