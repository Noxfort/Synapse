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
# File: src/factories/imputer_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.imputer_agent import ImputerAgent
from src.services.imputer_pipeline import ImputerPipeline
from src.services.imputer_trainer import ImputerTrainer


class ImputerFactory:
    """
    Dedicated Creational Factory for the Imputer Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles ImputerPipeline, ImputerTrainer, and injects them into ImputerAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        feature_dim: int = 4,
        **kwargs: Any
    ) -> ImputerAgent:
        cfg = (config or {}).get('imputer', {})

        seq_len = kwargs.get('seq_len', cfg.get('seq_len', 24))
        patch_len = kwargs.get('patch_len', cfg.get('patch_len', 8))
        stride = kwargs.get('stride', cfg.get('stride', 4))
        d_model = kwargs.get('d_model', cfg.get('d_model', 64))
        n_heads = kwargs.get('n_heads', cfg.get('n_heads', 4))
        n_layers = kwargs.get('n_layers', cfg.get('n_layers', 2))
        dropout = kwargs.get('dropout', cfg.get('dropout', 0.1))
        learning_rate = kwargs.get('learning_rate', cfg.get('lr', 0.001))

        pipeline = ImputerPipeline(
            feature_dim=feature_dim,
            seq_len=seq_len,
            patch_len=patch_len,
            stride=stride,
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            dropout=dropout
        )

        trainer = ImputerTrainer(
            model=pipeline.model,
            learning_rate=learning_rate,
            device=pipeline.device
        )

        return ImputerAgent(
            pipeline=pipeline,
            trainer=trainer,
            feature_dim=feature_dim,
            seq_len=seq_len,
            patch_len=patch_len,
            stride=stride,
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            dropout=dropout,
            learning_rate=learning_rate
        )
