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
# File: src/interfaces/agents.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Protocol, runtime_checkable
from src.interfaces.base import IDeviceMovable


@runtime_checkable
class IAgent(IDeviceMovable, Protocol):
    """Base contract for any AI Agent in the system."""
    ...


@runtime_checkable
class ISpatialAgent(IAgent, Protocol):
    """Contract for agents that understand space (e.g. GATv2)."""
    def process_region(self, node_features: Any, edge_index: Any) -> Any:
        """Processes a graph snapshot and returns node embeddings."""
        ...


@runtime_checkable
class ITemporalAgent(IAgent, Protocol):
    """Contract for agents that understand time (e.g. Transformers / TCN)."""
    def predict_state(self, history: Any) -> Any:
        """Predicts future states based on historical time-series."""
        ...
