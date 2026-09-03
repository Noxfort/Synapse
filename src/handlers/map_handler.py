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
# File: src/handlers/map_handler.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Map & Topology Command Handler (SOLID: SRP & DIP).

Translates IPC actions related to road network graph parsing and topology visualization.
Injected with AppState and MapService to avoid inline runtime instantiations.
"""

import os
from urllib.parse import unquote, urlparse
from typing import Any, Dict, Optional

from src.ipc.ipc_protocol import IpcMessage
from src.ipc.command_router import Responder
from src.ipc.serializers import TopologySerializer
from src.logging.facade import get_logger


class MapCommandHandler:
    """Handles map network parsing, topology loading, and state hydration."""

    def __init__(self, app_state: Any, map_service: Optional[Any] = None):
        self.logger = get_logger("MapCommandHandler")
        self.app_state = app_state
        if map_service is not None:
            self.map_service = map_service
        else:
            from src.services.map_service import MapService
            self.map_service = MapService()

    def handle_load_map(self, msg: IpcMessage, responder: Responder) -> None:
        raw_path = msg.payload.get("path", "")
        self.logger.info(f"📍 [MapCommandHandler] Recebida solicitação 'load_map' para: '{raw_path}'")

        if not raw_path or not str(raw_path).strip():
            err_msg = "Caminho do arquivo de rede viária não fornecido."
            self.logger.error(f"❌ [MapCommandHandler] {err_msg}")
            responder(False, error=err_msg)
            return

        # Normalize path
        clean_path = str(raw_path).strip().strip('"\'')
        if clean_path.startswith("file://"):
            clean_path = unquote(urlparse(clean_path).path)
        clean_path = unquote(clean_path)
        clean_path = os.path.expanduser(clean_path)

        if not os.path.exists(clean_path):
            err_msg = f"Arquivo de mapa não encontrado no disco: {clean_path}"
            self.logger.error(f"❌ [MapCommandHandler] {err_msg}")
            responder(False, error=err_msg)
            return

        ok = self.map_service.load_network(clean_path)
        if not ok:
            err_msg = getattr(self.map_service, "last_error", None) or f"Erro ao processar rede viária SUMO (.net.xml / .net.xml.gz): {clean_path}"
            self.logger.error(f"❌ [MapCommandHandler] {err_msg}")
            responder(False, error=err_msg)
            return

        # Hydrate domain topology repository through public domain interface
        nodes = getattr(self.map_service, "nodes", [])
        edges = getattr(self.map_service, "edges", [])

        nodes_data = [
            {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "type": getattr(n, "node_type", "junction"),
                "name": getattr(n, "real_name", None),
                "tl_logic_id": getattr(n, "tl_logic_id", None),
            }
            for n in nodes
        ]
        edges_data = [
            {
                "id": e.id,
                "from": e.from_node,
                "to": e.to_node,
                "shape": getattr(e, "shape", []),
                "name": getattr(e, "real_name", None),
                "length": getattr(e, "length", 100.0),
                "weight": getattr(e, "weight", 1.0),
                "max_speed": getattr(e, "max_speed", 13.89),
                "lanes": getattr(e, "lanes", 1),
            }
            for e in edges
        ]

        if hasattr(self.app_state, "set_map_data"):
            self.app_state.set_map_data(nodes_data, edges_data)
        elif hasattr(self.app_state, "topology") and hasattr(self.app_state.topology, "load_data"):
            self.app_state.topology.load_data(nodes_data, edges_data)

        if hasattr(self.app_state, "set_map_source_path"):
            self.app_state.set_map_source_path(os.path.abspath(clean_path))

        self.logger.info(
            f"✅ [MapCommandHandler] Rede viária SUMO carregada com sucesso! "
            f"Arquivo: '{clean_path}' | Nós: {len(nodes_data)} | Arestas: {len(edges_data)}"
        )

        topo = TopologySerializer.serialize_topology(self.app_state)
        responder(True, topo)

    def handle_get_topology(self, msg: IpcMessage) -> Dict[str, Any]:
        self.logger.info("📍 [MapCommandHandler] Solicitando topologia atual do AppState")
        # Auto-hydrate if map_path is restored from disk but nodes not yet loaded into memory
        map_path = self.app_state.get_map_source_path() if hasattr(self.app_state, "get_map_source_path") else None
        if map_path and os.path.exists(map_path) and hasattr(self.app_state, "get_all_nodes"):
            nodes = self.app_state.get_all_nodes()
            if not nodes:
                self.logger.info(f"📍 [MapCommandHandler] Auto-hydrating topology from restored map path: '{map_path}'")
                if self.map_service.load_network(map_path):
                    svc_nodes = getattr(self.map_service, "nodes", [])
                    svc_edges = getattr(self.map_service, "edges", [])
                    nodes_data = [
                        {
                            "id": n.id,
                            "x": n.x,
                            "y": n.y,
                            "type": getattr(n, "node_type", "junction"),
                            "name": getattr(n, "real_name", None),
                            "tl_logic_id": getattr(n, "tl_logic_id", None),
                        }
                        for n in svc_nodes
                    ]
                    edges_data = [
                        {
                            "id": e.id,
                            "from": e.from_node,
                            "to": e.to_node,
                            "shape": getattr(e, "shape", []),
                            "name": getattr(e, "real_name", None),
                            "length": getattr(e, "length", 100.0),
                            "weight": getattr(e, "weight", 1.0),
                            "max_speed": getattr(e, "max_speed", 13.89),
                            "lanes": getattr(e, "lanes", 1),
                        }
                        for e in svc_edges
                    ]
                    if hasattr(self.app_state, "set_map_data"):
                        self.app_state.set_map_data(nodes_data, edges_data)
                    elif hasattr(self.app_state, "topology") and hasattr(self.app_state.topology, "load_data"):
                        self.app_state.topology.load_data(nodes_data, edges_data)

        return TopologySerializer.serialize_topology(self.app_state)
