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
# File: src/factories/specialist_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.specialist_agent import SpecialistAgent
from src.pipeline.specialist_pipeline import SpecialistPipeline
from src.trainer.specialist_trainer import SpecialistTrainer


class SpecialistFactory:
    """
    Dedicated Creational Factory for the Specialist Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles SpecialistPipeline, SpecialistTrainer, and injects them into SpecialistAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        input_dim: int = 1,
        output_dim: int = 32,
        **kwargs: Any
    ) -> SpecialistAgent:
        cfg = (config or {}).get('specialist', {})

        num_channels = kwargs.get('num_channels')
        if num_channels is None:
            if 'num_levels' in cfg and 'base_channel' in cfg:
                num_channels = [cfg['base_channel']] * cfg['num_levels']
            else:
                num_channels = [16, 32]

        kernel_size = kwargs.get('kernel_size', cfg.get('kernel_size', 2))
        dropout = kwargs.get('dropout', cfg.get('dropout', 0.2))
        learning_rate = kwargs.get('learning_rate', cfg.get('lr', 0.001))

        pipeline = SpecialistPipeline(
            input_dim=input_dim,
            output_dim=output_dim,
            num_channels=num_channels,
            kernel_size=kernel_size,
            dropout=dropout
        )

        trainer = SpecialistTrainer(
            model=pipeline.model,
            input_dim=input_dim,
            output_dim=output_dim,
            learning_rate=learning_rate,
            device=pipeline._get_current_device()
        )

        return SpecialistAgent(
            pipeline=pipeline,
            trainer=trainer,
            input_dim=input_dim,
            output_dim=output_dim,
            num_channels=num_channels,
            kernel_size=kernel_size,
            dropout=dropout,
            learning_rate=learning_rate
        )
