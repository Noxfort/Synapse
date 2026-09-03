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
# File: src/adapters/base_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import abc
import threading
from typing import Any, Dict, Optional

from src.domain.entities import DataSource
from src.interfaces.ingestion_adapters import IIngestionAdapter, PacketCallback
from src.utils.logging_setup import get_logger


class BaseIngestionAdapter(abc.ABC):
    """
    Abstract Base Ingestion Adapter (Template Method & Common Infrastructure).
    Encapsulates thread safety, lifecycle state, and packet forwarding logic.
    """

    def __init__(self, adapter_id: str, transport_name: str):
        self._adapter_id = adapter_id
        self._transport_name = transport_name
        self._is_running = False
        self._lock = threading.Lock()
        self._callback: Optional[PacketCallback] = None
        self._logger = get_logger(f"Adapter.{self._adapter_id}")

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def transport_name(self) -> str:
        return self._transport_name

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def start(self, on_packet_received: PacketCallback) -> None:
        """Starts the adapter and assigns the central packet callback."""
        with self._lock:
            self._callback = on_packet_received
            if self._is_running:
                self._logger.warning(f"Adapter '{self._adapter_id}' is already running.")
                return
            self._is_running = True

        self._logger.info(f"🚀 [IngestionAdapter] Starting adapter '{self._adapter_id}' ({self._transport_name})...")
        self._do_start()

    def stop(self) -> None:
        """Gracefully stops the adapter."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False

        self._logger.info(f"🛑 [IngestionAdapter] Stopping adapter '{self._adapter_id}' ({self._transport_name})...")
        self._do_stop()

    def register_source(self, source: DataSource) -> None:
        """Hook for registering a DataSource."""
        pass

    def unregister_source(self, source_id: str) -> None:
        """Hook for unregistering a DataSource."""
        pass

    def check_poll(self, current_time: float) -> None:
        """Periodic hook for polling adapters."""
        pass

    def emit_packet(self, source_id: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Thread-safe packet dispatcher towards the central callback.
        Attaches default transport metadata if none provided.
        """
        cb = self._callback
        if cb:
            meta = metadata or {}
            if "transport" not in meta:
                meta["transport"] = self._transport_name
            if "adapter_id" not in meta:
                meta["adapter_id"] = self._adapter_id
            try:
                cb(str(source_id), payload, meta)
            except Exception as e:
                self._logger.error(f"Error in packet callback for '{source_id}': {e}", exc_info=True)

    @abc.abstractmethod
    def _do_start(self) -> None:
        """Specific startup logic for the concrete transport."""
        raise NotImplementedError

    @abc.abstractmethod
    def _do_stop(self) -> None:
        """Specific teardown logic for the concrete transport."""
        raise NotImplementedError
