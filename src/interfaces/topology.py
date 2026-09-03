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
# File: src/interfaces/topology.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from typing import Dict, List, Optional, Protocol, runtime_checkable
from src.domain.entities import MapNode, MapEdge


@runtime_checkable
class ITopologyReader(Protocol):
    """
    Read-only contract for static road network topology.
    (ISP: Segregated read interface for inference and graph builders).
    """

    def get_all_nodes(self) -> List[MapNode]:
        """Retrieve all nodes in the road network."""
        ...

    def get_all_edges(self) -> List[MapEdge]:
        """Retrieve all edges in the road network."""
        ...

    def get_node(self, node_id: str) -> Optional[MapNode]:
        """Retrieve a specific node by ID."""
        ...

    def get_edge(self, edge_id: str) -> Optional[MapEdge]:
        """Retrieve a specific edge by ID."""
        ...

    def get_map_file_path(self) -> Optional[str]:
        """Retrieve the active map file path."""
        ...


@runtime_checkable
class ITopologyRepository(ITopologyReader, Protocol):
    """
    Contract for in-memory pure domain repository managing static map topology.
    (SRP: Pure in-memory road network domain state management).
    """

    def load_data(self, nodes_data: List[dict], edges_data: List[dict]) -> None:
        """Load and hydrate nodes and edges data."""
        ...

    def clear(self) -> None:
        """Clear all nodes, edges, and active map path."""
        ...

    def set_map_file_path(self, path: Optional[str]) -> None:
        """Set the active map file path."""
        ...
