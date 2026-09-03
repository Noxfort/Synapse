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
# File: src/adapters/http_push_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from typing import Any, Dict, Optional

from src.domain.entities import DataSource
from src.adapters.base_adapter import BaseIngestionAdapter
from src.infrastructure.sensor_gateway import SensorGateway
from src.interfaces.sensor_gateway import IPolyglotPayloadParser, ISensorIdExtractor


class HttpPushAdapter(BaseIngestionAdapter):
    """
    HTTP PUSH / Webhook Ingestion Adapter.
    Exposes an HTTP server for Edge AI cameras, radars, and roadside units to POST telemetry.
    Delegates packet parsing to PolyglotPayloadParser and heuristic ID resolution to SensorIdExtractor.
    """

    def __init__(
        self,
        adapter_id: str = "http_push_gateway",
        host: str = "0.0.0.0",
        port: int = 8080,
        parser_registry: Optional[IPolyglotPayloadParser] = None,
        id_extractor: Optional[ISensorIdExtractor] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(adapter_id=adapter_id, transport_name="HTTP-Push")
        self.host = host
        self.port = port
        self.api_key = api_key
        self.gateway = SensorGateway(
            host=self.host,
            port=self.port,
            parser_registry=parser_registry,
            id_extractor=id_extractor,
        )
        # Connect listener permanently so packets received directly or via HTTP server always flow
        self.gateway.register_listener(self._on_gateway_data)
        self.gateway.server_error.connect(self._on_gateway_error)

    def _do_start(self) -> None:
        """Starts the gateway server thread."""
        self.gateway.start()

    def _do_stop(self) -> None:
        """Stops the underlying HTTP server."""
        self.gateway.stop()

    def _on_gateway_data(self, source_id: str, payload: Dict[str, Any]) -> None:
        """Invoked when the SensorGateway decodes an inbound HTTP POST packet."""
        self.emit_packet(
            source_id=source_id,
            payload=payload,
            metadata={
                "transport": "HTTP-Push",
                "host": self.host,
                "port": self.port,
            },
        )

    def _on_gateway_error(self, error_msg: str) -> None:
        self._logger.error(f"[HttpPushAdapter] Gateway Error: {error_msg}")

    def register_source(self, source: DataSource) -> None:
        """Allows registering specific expected local sources."""
        self._logger.debug(f"[HttpPushAdapter] Registered local push source '{source.id}' ({source.name})")

    def unregister_source(self, source_id: str) -> None:
        self._logger.debug(f"[HttpPushAdapter] Unregistered local push source '{source_id}'")
