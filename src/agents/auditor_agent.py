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
# File: src/agents/auditor_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
from typing import Dict, Any, Union, Optional

from src.agents.base_agent import BaseAgent
from src.domain.interfaces import IAuditorPipeline, IAuditorTrainer
from src.services.auditor_pipeline import AuditorPipeline
from src.services.auditor_trainer import AuditorTrainer


class AuditorAgent(BaseAgent):
    """
    The Auditor Agent ('O Segurança').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: High-level security auditing and anomaly detection.
    - Delegations:
      -> Neural Pipeline & Scoring: IAuditorPipeline (src/services/auditor_pipeline.py)
      -> Neural Optimization & Calibration: IAuditorTrainer (src/services/auditor_trainer.py)
    """

    def __init__(
        self,
        pipeline: Optional[IAuditorPipeline] = None,
        trainer: Optional[IAuditorTrainer] = None,
        input_len: int = 60,
        J: int = 2,
        Q: int = 1,
        latent_dim: int = 16,
        learning_rate: float = 1e-3,
        physics_weight: float = 0.5,
        max_acceleration: float = 10.0,
        enable_pinn: bool = True,
        name: str = "AuditorAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = AuditorPipeline(
                input_len=input_len,
                J=J,
                Q=Q,
                latent_dim=latent_dim,
                physics_weight=physics_weight,
                max_acceleration=max_acceleration,
                enable_pinn=enable_pinn
            )

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: IAuditorPipeline = pipeline
        self.trainer: IAuditorTrainer = trainer or AuditorTrainer(
            model=self.model,
            learning_rate=learning_rate,
            physics_weight=physics_weight,
            enable_pinn=enable_pinn,
            device=getattr(self.pipeline, "device", None)
        )

    def inference(self, input_data: Union[Dict[str, Any], torch.Tensor]) -> Dict[str, Any]:
        """Unified inference entry point."""
        return self.audit(input_data)

    def audit(self, input_data: Union[Dict[str, Any], torch.Tensor]) -> Dict[str, Any]:
        """Delegates security and physics auditing to AuditorPipeline."""
        return self.pipeline.audit(input_data)

    def train_step(self, input_data: Any) -> float:
        """Delegates optimization and adaptive threshold updates to AuditorTrainer."""
        return self.trainer.train_step(input_data)