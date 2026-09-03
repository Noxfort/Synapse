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
# File: src/workers/ingestion_worker.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import time
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# --- Domain & Ingestion Adapters ---
from src.domain.app_state import AppState
from src.domain.entities import DataSource
from src.adapters.http_poller_adapter import HttpPollerAdapter
from src.adapters.http_push_adapter import HttpPushAdapter
from src.adapters.ingestion_hub import IngestionHub
from src.adapters.mqtt_adapter import MqttIngestionAdapter
from src.adapters.websocket_adapter import WebSocketIngestionAdapter
from src.infrastructure.sensor_gateway import SensorGateway
from src.pipeline.ingestion_pipeline import IngestionPipeline
from src.utils.logging_setup import get_logger

logger = get_logger("IngestionWorker")


class IngestionWorker(QObject):
    """
    Worker dedicated to Data Ingestion (The 'Mouth' of the System).
    
    Agnostic Architecture (SOLID & Hexagonal Ingestion):
    - [SRP] Orchestrates the IngestionHub and delegates transport protocols to modular adapters.
    - [OCP] Supports dynamic registration of custom adapters (HTTP Push, HTTP Poller, MQTT, WebSockets, File Replay).
    - [LSP] Pure decoupling: Zero Trust Pipeline, LinguistAgent and InferenceEngine remain 100% transport-blind.
    - [DIP] Relies on IngestionHub and IIngestionAdapter abstraction layers.
    """
    
    # Qt Signal emitted when valid, authenticated data passes the Zero Trust pipeline
    # Arguments: source_id (str), payload (dict/object)
    data_ready = pyqtSignal(str, object)

    def __init__(self, app_state: AppState, hub: Optional[IngestionHub] = None):
        super().__init__()
        self.app_state = app_state
        
        # 1. Zero Trust Pipeline (Pure Verification & Buffering)
        self.pipeline = IngestionPipeline(self.app_state)
        
        # 2. Agnostic Ingestion Hub
        self.hub = hub or IngestionHub(self.pipeline)
        
        # 3. Default Transport Adapters
        self.push_adapter = HttpPushAdapter(
            adapter_id="http_push_gateway",
            host="0.0.0.0",
            port=8080,
        )
        self.poller_adapter = HttpPollerAdapter(
            adapter_id="http_poller_global",
            max_workers=4,
            fast_poll_interval=10.0,
            normal_poll_interval=300.0,
        )
        self.mqtt_adapter = MqttIngestionAdapter(
            adapter_id="mqtt_broker_adapter",
        )
        self.ws_adapter = WebSocketIngestionAdapter(
            adapter_id="websocket_stream_adapter",
        )

        # Register default adapters in Hub
        self.hub.register_adapter(self.push_adapter)
        self.hub.register_adapter(self.poller_adapter)
        self.hub.register_adapter(self.mqtt_adapter)
        self.hub.register_adapter(self.ws_adapter)

        # Subscribe to hub's accepted packet stream
        self.hub.register_listener(self._handle_hub_packet)

        # Sync existing data sources from state into adapters
        self._sync_registered_sources()

    @property
    def gateway(self) -> SensorGateway:
        """Backward-compatible access to the underlying HTTP Push SensorGateway."""
        return self.push_adapter.gateway

    def _sync_registered_sources(self) -> None:
        """Populates all adapters with currently registered data sources."""
        sources = self.app_state.get_all_data_sources()
        for src in sources:
            self.hub.register_source(src)

    def start(self) -> None:
        """Starts all ingestion adapters."""
        logger.info("[IngestionWorker] Starting Ingestion Hub and Transport Adapters...")
        self._sync_registered_sources()
        self.hub.start_all()
        logger.info("[IngestionWorker] 🚀 Transport Adapters Online (HTTP Push, Poller, MQTT, WebSocket).")

    def stop(self) -> None:
        """Gracefully stops all ingestion adapters."""
        logger.info("[IngestionWorker] Stopping network services and adapters...")
        self.hub.stop_all()

    def check_global_fetch(self, current_time: float) -> None:
        """
        Called by the main cycle to evaluate polling checks across adapters.
        """
        # Ensure new/updated sources are synced to poller
        self._sync_registered_sources()
        self.hub.check_poll(current_time)

    def get_pipeline(self) -> IngestionPipeline:
        """Exposes the pipeline for Linguist/Quarantine checks."""
        return self.pipeline

    def _handle_hub_packet(self, source_id: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Invoked when an accepted packet is authenticated by the Zero Trust pipeline.
        Emits thread-safe Qt data_ready signal downstream to InferenceEngine and UI.
        """
        self.data_ready.emit(source_id, payload)
