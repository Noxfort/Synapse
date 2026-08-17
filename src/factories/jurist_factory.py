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
# File: src/factories/jurist_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

from src.agents.jurist_agent import JuristAgent


class JuristFactory:
    """
    Dedicated Creational Factory for the Jurist Subsystem.
    
    SOLID Compliance (SRP):
    - Sole Responsibility: Instantiates JuristAgent configured with the target LLM Model Vault identifier.
    """

    @staticmethod
    def create(
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> JuristAgent:
        cfg = (config or {}).get('jurist', {})
        model_id = kwargs.get('model_id', cfg.get('model_id'))
        return JuristAgent(model_id=model_id)
