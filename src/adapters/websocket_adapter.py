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
# File: src/adapters/websocket_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import json
from typing import Any, Dict, Optional

from src.domain.entities import DataSource
from src.adapters.base_adapter import BaseIngestionAdapter


class WebSocketIngestionAdapter(BaseIngestionAdapter):
    """
    WebSocket / Streaming Ingestion Adapter.
    Receives real-time streaming metadata packets from Edge AI camera pipelines.
    Supports continuous event feeds and high-frequency frame detections.
    """

    def __init__(
        self,
        adapter_id: str = "websocket_stream_adapter",
        uri: Optional[str] = None,
        is_server: bool = False,
        port: int = 8765,
    ):
        super().__init__(adapter_id=adapter_id, transport_name="WebSocket")
        self.uri = uri
        self.is_server = is_server
        self.port = port
        self._clients: list = []

    def _do_start(self) -> None:
        self._logger.info(
            f"⚡ [WebSocketAdapter] Adapter '{self._adapter_id}' initialized "
            f"({'Server on port ' + str(self.port) if self.is_server else 'Client target ' + str(self.uri)})."
        )

    def _do_stop(self) -> None:
        self._logger.info(f"🛑 [WebSocketAdapter] Adapter '{self._adapter_id}' stopped.")

    def handle_stream_frame(self, source_id: str, frame_data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Receives an inbound WebSocket frame/event and forwards directly to the pipeline.
        """
        meta = metadata or {}
        meta.setdefault("transport", "WebSocket")
        meta.setdefault("adapter_id", self._adapter_id)
        self.emit_packet(source_id=source_id, payload=frame_data, metadata=meta)
