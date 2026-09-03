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
# File: src/adapters/ingestion_hub.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import threading
from typing import Any, Callable, Dict, List, Optional

from src.domain.entities import DataSource
from src.interfaces.ingestion_adapters import IIngestionAdapter, IIngestionHub
from src.pipeline.ingestion_pipeline import IngestionPipeline
from src.utils.logging_setup import get_logger

logger = get_logger("IngestionHub")


class IngestionHub:
    """
    Central Ingestion Hub & Composite Orchestrator (SOLID Architecture).
    
    Responsibilities:
    - [SRP] Unifies multi-protocol ingestion adapters and routes incoming packets to the Zero Trust pipeline.
    - [OCP] Open for custom transport adapters (HTTP, MQTT, WebSockets, gRPC, File Replay) via register_adapter().
    - [LSP] Conforms to IIngestionHub protocol.
    - [ISP] Simple routing and lifecycle hooks.
    - [DIP] Decoupled from transport specifics; downstream pipeline only receives normalized (source_id, payload).
    """

    def __init__(self, pipeline: IngestionPipeline):
        self.pipeline = pipeline
        self._adapters: Dict[str, IIngestionAdapter] = {}
        self._listeners: List[Callable[[str, Any, Optional[Dict[str, Any]]], None]] = []
        self._lock = threading.Lock()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def register_adapter(self, adapter: IIngestionAdapter) -> None:
        """Registers a new transport adapter in the hub."""
        with self._lock:
            if adapter.adapter_id in self._adapters:
                logger.warning(f"[IngestionHub] Adapter '{adapter.adapter_id}' already registered. Replacing...")
            self._adapters[adapter.adapter_id] = adapter
            # Bind callback so adapter can forward packets immediately
            if hasattr(adapter, '_callback'):
                adapter._callback = self.route_packet
            logger.info(f"🔌 [IngestionHub] Registered adapter '{adapter.adapter_id}' ({adapter.transport_name})")

        # If hub is already running, immediately start the newly registered adapter
        if self._is_running:
            adapter.start(self.route_packet)

    def unregister_adapter(self, adapter_id: str) -> Optional[IIngestionAdapter]:
        """Stops and removes an adapter by ID."""
        with self._lock:
            adapter = self._adapters.pop(adapter_id, None)

        if adapter:
            if adapter.is_running:
                adapter.stop()
            logger.info(f"🔌 [IngestionHub] Unregistered adapter '{adapter_id}'")
        return adapter

    def get_adapter(self, adapter_id: str) -> Optional[IIngestionAdapter]:
        with self._lock:
            return self._adapters.get(adapter_id)

    def get_all_adapters(self) -> List[IIngestionAdapter]:
        with self._lock:
            return list(self._adapters.values())

    def register_listener(self, callback: Callable[[str, Any, Optional[Dict[str, Any]]], None]) -> None:
        """Subscribes a listener to receive successfully validated packets."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[str, Any, Optional[Dict[str, Any]]], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def start_all(self) -> None:
        """Starts all registered adapters and begins routing data."""
        with self._lock:
            self._is_running = True
            adapters = list(self._adapters.values())

        logger.info(f"🚀 [IngestionHub] Starting all {len(adapters)} ingestion adapters...")
        for adapter in adapters:
            try:
                adapter.start(self.route_packet)
            except Exception as e:
                logger.error(f"❌ [IngestionHub] Failed to start adapter '{adapter.adapter_id}': {e}", exc_info=True)

    def stop_all(self) -> None:
        """Stops all registered adapters gracefully."""
        with self._lock:
            self._is_running = False
            adapters = list(self._adapters.values())

        logger.info(f"🛑 [IngestionHub] Stopping all {len(adapters)} ingestion adapters...")
        for adapter in adapters:
            try:
                adapter.stop()
            except Exception as e:
                logger.error(f"❌ [IngestionHub] Error stopping adapter '{adapter.adapter_id}': {e}", exc_info=True)

    def route_packet(self, source_id: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        The Central Funnel:
        Receives data from any transport adapter, passes it through the Zero Trust pipeline,
        and dispatches to downstream consumers if authenticated.
        """
        if not source_id:
            return False

        # 1. Zero Trust Pipeline Authentication & Quarantine/Active Buffering
        is_accepted = self.pipeline.process_packet(source_id, payload)

        # 2. Notify Listeners if accepted
        if is_accepted:
            for listener in list(self._listeners):
                try:
                    listener(source_id, payload, metadata)
                except Exception as e:
                    logger.error(f"❌ [IngestionHub] Error in packet listener: {e}", exc_info=True)

        return is_accepted

    def register_source(self, source: DataSource) -> None:
        """Propagates new DataSource to all registered adapters."""
        with self._lock:
            adapters = list(self._adapters.values())
        for adapter in adapters:
            try:
                adapter.register_source(source)
            except Exception as e:
                logger.error(f"[IngestionHub] Error registering source in '{adapter.adapter_id}': {e}")

    def unregister_source(self, source_id: str) -> None:
        """Propagates source removal to all registered adapters."""
        with self._lock:
            adapters = list(self._adapters.values())
        for adapter in adapters:
            try:
                adapter.unregister_source(source_id)
            except Exception as e:
                logger.error(f"[IngestionHub] Error unregistering source in '{adapter.adapter_id}': {e}")

    def check_poll(self, current_time: float) -> None:
        """Periodic trigger delegating to polling adapters."""
        with self._lock:
            adapters = list(self._adapters.values())
        for adapter in adapters:
            try:
                adapter.check_poll(current_time)
            except Exception as e:
                logger.error(f"[IngestionHub] Error during check_poll in '{adapter.adapter_id}': {e}")
