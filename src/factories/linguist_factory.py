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
# File: src/factories/linguist_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.linguist_agent import LinguistAgent
from src.pipeline.linguist_pipeline import LinguistPipeline
from src.trainer.linguist_trainer import LinguistTrainer
from src.utils.model_paths import get_distilroberta_base_path


class LinguistFactory:
    """
    Dedicated Creational Factory for the Linguist Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles LinguistPipeline, LinguistTrainer, and injects them into LinguistAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> LinguistAgent:
        cfg = (config or {}).get('linguist', {})

        model_name = kwargs.get('model_name', cfg.get('model_name', get_distilroberta_base_path()))
        learning_rate = kwargs.get('learning_rate', cfg.get('lr', 1e-4))

        pipeline = LinguistPipeline(model_name=model_name)
        trainer = LinguistTrainer(
            model=pipeline.model,
            tokenizer=pipeline.tokenizer,
            model_name=model_name,
            learning_rate=learning_rate,
            device=pipeline.device
        )

        return LinguistAgent(
            pipeline=pipeline,
            trainer=trainer,
            model_name=model_name,
            learning_rate=learning_rate
        )
