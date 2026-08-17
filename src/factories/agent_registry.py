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
# File: src/factories/agent_registry.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional


class AgentRegistry:
    """
    Dedicated in-memory Registry & Object Pool for active AI Agents per sensor source.
    
    SOLID Compliance (SRP):
    - Sole Responsibility: Stores, retrieves, and evicts active agent instances by source_id.
    - Zero creational logic: Does not instantiate neural networks or pipelines.
    """

    def __init__(self):
        # Internal storage: { source_id: { agent_type: instance } }
        self._registry: Dict[str, Dict[str, Any]] = {}

    def get(self, source_id: str, agent_type: str) -> Optional[Any]:
        """Retrieves an active agent instance for a given source and type."""
        return self._registry.get(source_id, {}).get(agent_type)

    def register(self, source_id: str, agent_type: str, agent: Any) -> None:
        """Registers an active agent instance under a given source and type."""
        if source_id not in self._registry:
            self._registry[source_id] = {}
        self._registry[source_id][agent_type] = agent

    def has(self, source_id: str, agent_type: str) -> bool:
        """Checks whether an agent of a given type exists for the source."""
        return agent_type in self._registry.get(source_id, {})

    def remove(self, source_id: str, agent_type: Optional[str] = None) -> None:
        """Removes a specific agent or all agents for a source."""
        if source_id in self._registry:
            if agent_type is not None:
                self._registry[source_id].pop(agent_type, None)
                if not self._registry[source_id]:
                    self._registry.pop(source_id, None)
            else:
                self._registry.pop(source_id, None)

    def clear(self) -> None:
        """Clears all registered agent instances."""
        self._registry.clear()
