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
# File: src/ipc/serializers.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
IPC Data Transfer Object (DTO) Serializers (SOLID: SRP).

Encapsulates the transformation of domain entities and state into UI-ready payload structures.
"""

from typing import Dict, Any, List
from src.domain.app_state import AppState


class TopologySerializer:
    """Serializes road network topology into frontend React visualizer format."""

    @staticmethod
    def serialize_topology(app_state: AppState) -> Dict[str, Any]:
        """Serializes current map graph for the React visualizer."""
        try:
            nodes_list = []
            raw_nodes = app_state.get_all_nodes() if hasattr(app_state, "get_all_nodes") else []
            for n in raw_nodes:
                nodes_list.append({
                    "id": n.id,
                    "x": n.x,
                    "y": n.y,
                    "is_tls": getattr(n, "is_tls", bool(getattr(n, "tl_logic_id", False))),
                })

            edges_list = []
            raw_edges = app_state.get_all_edges() if hasattr(app_state, "get_all_edges") else []
            for e in raw_edges:
                edges_list.append({
                    "id": e.id,
                    "from": e.from_node,
                    "to": e.to_node,
                    "length": getattr(e, "length", 0.0),
                    "shape": getattr(e, "shape", []),
                })

            is_loaded = bool(nodes_list or edges_list)
            return {"nodes": nodes_list, "edges": edges_list, "loaded": is_loaded}
        except Exception as ex:
            return {"nodes": [], "edges": [], "loaded": False, "error": str(ex)}
