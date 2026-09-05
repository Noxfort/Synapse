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
# File: src/factories/compass_factory.py
# Author: Gabriel Moraes
# Date: 2026-09-05

from typing import Dict, Any, Optional

from src.agents.compass_agent import CompassAgent
from src.pipeline.compass_pipeline import CompassPipeline
from src.utils.model_paths import get_distilroberta_base_path


class CompassFactory:
    """
    Dedicated Creational Factory for the Compass Subsystem.
    
    SOLID Compliance (SRP / DIP):
    - Sole Responsibility: Assembles CompassPipeline and injects into CompassAgent.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> CompassAgent:
        cfg = (config or {}).get('compass', {})
        model_name = kwargs.get('model_name', cfg.get('model_name', get_distilroberta_base_path()))
        confidence_threshold = kwargs.get('confidence_threshold', cfg.get('confidence_threshold', 0.65))

        pipeline = CompassPipeline(
            model_name=model_name,
            confidence_threshold=confidence_threshold
        )

        return CompassAgent(
            pipeline=pipeline,
            model_name=model_name
        )
