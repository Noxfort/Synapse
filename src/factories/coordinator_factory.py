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
# File: src/factories/coordinator_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.coordinator_agent import CoordinatorAgent
from src.pipeline.coordinator_pipeline import CoordinatorPipeline
from src.trainer.coordinator_trainer import CoordinatorTrainer


class CoordinatorFactory:
    """
    Dedicated Creational Factory for the Coordinator Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles CoordinatorPipeline, CoordinatorTrainer, and injects them into CoordinatorAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        input_dim: int = 32,
        hidden_dim: int = 32,
        output_dim: int = 32,
        **kwargs: Any
    ) -> CoordinatorAgent:
        cfg = (config or {}).get('coordinator', {})

        heads = kwargs.get('heads', cfg.get('heads', 4))
        dropout = kwargs.get('dropout', cfg.get('dropout', 0.6))
        learning_rate = kwargs.get('learning_rate', cfg.get('lr', 0.005))
        hidden_channels = kwargs.get('hidden_channels', cfg.get('hidden_channels', hidden_dim))

        pipeline = CoordinatorPipeline(
            in_channels=input_dim,
            hidden_channels=hidden_channels,
            out_channels=output_dim,
            heads=heads,
            dropout=dropout
        )

        trainer = CoordinatorTrainer(
            model=pipeline.model,
            learning_rate=learning_rate,
            device=pipeline.device
        )

        return CoordinatorAgent(
            pipeline=pipeline,
            trainer=trainer,
            in_channels=input_dim,
            hidden_channels=hidden_channels,
            out_channels=output_dim,
            heads=heads,
            dropout=dropout,
            learning_rate=learning_rate
        )
