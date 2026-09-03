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
# File: src/handlers/source_handler.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Data Source & Sensor Command Handler (SOLID: SRP & DIP).

Translates IPC actions related to sensor registration, association to map elements,
and local/global scope toggling.
"""

import os
from typing import Any, Dict

from src.ipc.ipc_protocol import IpcMessage
from src.domain.entities import DataSource, SourceType, SourceStatus


class SourceCommandHandler:
    """Handles data source registration, association, and scope toggling."""

    def __init__(self, app_state: Any):
        self.app_state = app_state

    def handle_get_sources(self, msg: IpcMessage) -> Dict[str, Any]:
        sources_list = []
        raw_sources = []
        if hasattr(self.app_state, "get_all_data_sources"):
            raw_sources = self.app_state.get_all_data_sources()
        elif hasattr(self.app_state, "get_all_sources"):
            raw_sources = self.app_state.get_all_sources()

        for s in raw_sources:
            associated_element = None
            if hasattr(self.app_state, "get_element_for_source"):
                associated_element = self.app_state.get_element_for_source(s.id)
            elif hasattr(self.app_state, "sources") and hasattr(self.app_state.sources, "get_element_for_source"):
                associated_element = self.app_state.sources.get_element_for_source(s.id)

            sources_list.append({
                "id": s.id,
                "name": s.name,
                "is_local": s.is_local,
                "status": getattr(s.status, "value", str(s.status)),
                "semantic_type": getattr(s, "semantic_type", None) or "Scanning...",
                "latest_value": getattr(s, "latest_value", None),
                "confidence_score": getattr(s, "confidence_score", None),
                "associated_element": associated_element,
            })
        return {"sources": sources_list}

    def handle_add_source(self, msg: IpcMessage) -> Dict[str, Any]:
        payload = msg.payload
        name = payload.get("name", "New Source")
        is_local = payload.get("is_local", True)
        conn = payload.get("connection", "")
        stype = SourceType.API if not is_local else SourceType.MQTT
        src_id = payload.get("id") or f"src_{int(os.urandom(4).hex(), 16)}"

        src = DataSource(
            id=src_id,
            name=name,
            is_local=is_local,
            source_type=stype,
            connection_string=conn,
            status=SourceStatus.QUARANTINE,
        )
        self.app_state.add_data_source(src)
        return {"id": src.id, "name": src.name, "is_local": src.is_local}

    def handle_associate_source(self, msg: IpcMessage) -> Dict[str, Any]:
        source_id = msg.payload.get("source_id")
        element_id = msg.payload.get("element_id")
        if source_id and element_id:
            if hasattr(self.app_state, "sources") and hasattr(self.app_state.sources, "associate"):
                self.app_state.sources.associate(source_id, element_id)
            if hasattr(self.app_state, "data_association_changed") and hasattr(self.app_state.data_association_changed, "emit"):
                self.app_state.data_association_changed.emit(source_id, element_id)
        elif source_id:
            if hasattr(self.app_state, "enter_association_mode"):
                self.app_state.enter_association_mode(source_id)
            elif hasattr(self.app_state, "set_selected_source_for_association"):
                self.app_state.set_selected_source_for_association(source_id)
        elif element_id:
            if hasattr(self.app_state, "associate_selected_source_to_element"):
                self.app_state.associate_selected_source_to_element(element_id)
        return {"source_id": source_id, "element_id": element_id, "success": True}

    def handle_toggle_origin(self, msg: IpcMessage) -> Dict[str, Any]:
        sid = msg.payload.get("source_id")
        if sid and hasattr(self.app_state, "toggle_source_origin"):
            self.app_state.toggle_source_origin(sid)
        return {"source_id": sid}

    def handle_remove_source(self, msg: IpcMessage) -> Dict[str, Any]:
        sid = msg.payload.get("source_id")
        if sid and hasattr(self.app_state, "remove_data_source"):
            self.app_state.remove_data_source(sid)
        return {"source_id": sid}
