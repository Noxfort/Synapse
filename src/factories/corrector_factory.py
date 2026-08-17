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
# File: src/factories/corrector_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.corrector_agent import CorrectorAgent
from src.services.corrector_pipeline import CorrectorPipeline
from src.services.corrector_trainer import CorrectorTrainer


class CorrectorFactory:
    """
    Dedicated Creational Factory for the Corrector Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles CorrectorPipeline, CorrectorTrainer, and injects them into CorrectorAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        input_dim: int = 1,
        **kwargs: Any
    ) -> CorrectorAgent:
        cfg = (config or {}).get('corrector', {})

        hidden_dim = kwargs.get('hidden_dim', cfg.get('hidden_dim', 64))
        latent_dim = kwargs.get('latent_dim', cfg.get('latent_dim', 16))
        kernel_size = kwargs.get('kernel_size', cfg.get('kernel_size', 3))
        learning_rate = kwargs.get('learning_rate', cfg.get('lr', 0.001))
        physics_weight = kwargs.get('physics_weight', cfg.get('physics_weight', 0.1))
        max_acceleration = kwargs.get('max_acceleration', cfg.get('max_acceleration', 10.0))

        pipeline = CorrectorPipeline(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            latent_dim=latent_dim,
            kernel_size=kernel_size,
            max_acceleration=max_acceleration
        )

        trainer = CorrectorTrainer(
            model=pipeline.model,
            learning_rate=learning_rate,
            physics_weight=physics_weight,
            device=pipeline.device
        )

        return CorrectorAgent(
            pipeline=pipeline,
            trainer=trainer,
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            latent_dim=latent_dim,
            kernel_size=kernel_size,
            learning_rate=learning_rate,
            physics_weight=physics_weight,
            max_acceleration=max_acceleration
        )
