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
# File: src/interfaces/ingestion_adapters.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from src.domain.entities import DataSource


@dataclass
class IngestionPacket:
    """
    Normalized data packet passing from transport adapters into the Zero Trust pipeline.
    Encapsulates raw payload, device identifier, timestamp, and optional transport metadata.
    """
    source_id: str
    payload: Any
    timestamp: float = field(default_factory=time.time)
    transport_type: str = "unknown"
    client_info: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Callback type for receiving ingested packets: (source_id: str, payload: Any, metadata: Optional[Dict])
PacketCallback = Callable[[str, Any, Optional[Dict[str, Any]]], None]


@runtime_checkable
class IIngestionAdapter(Protocol):
    """
    Contract for modular transport ingestion adapters (Strategy Pattern).
    Decouples raw network / file I/O transport mechanisms from the Zero Trust Pipeline.
    """

    @property
    def adapter_id(self) -> str:
        """Unique identifier of the adapter instance (e.g. 'http_push_8080', 'mqtt_broker', 'poller_global')."""
        ...

    @property
    def transport_name(self) -> str:
        """Name of the underlying transport protocol (e.g. 'HTTP-Push', 'HTTP-Poller', 'MQTT', 'WebSocket', 'FileReplay')."""
        ...

    @property
    def is_running(self) -> bool:
        """Returns whether the adapter is actively listening or polling."""
        ...

    def start(self, on_packet_received: PacketCallback) -> None:
        """
        Starts the transport adapter and registers the central packet arrival callback.
        """
        ...

    def stop(self) -> None:
        """
        Gracefully stops the adapter and frees all underlying network sockets or thread pools.
        """
        ...

    def register_source(self, source: DataSource) -> None:
        """
        Registers a DataSource with this adapter (e.g. adding to poll list or topic subscription).
        """
        ...

    def unregister_source(self, source_id: str) -> None:
        """
        Unregisters a DataSource from this adapter.
        """
        ...

    def check_poll(self, current_time: float) -> None:
        """
        Periodic hook called by the engine/cycle for polling-based adapters.
        """
        ...


@runtime_checkable
class IIngestionHub(Protocol):
    """
    Contract for the Central Ingestion Hub (Composite & Router Pattern).
    Aggregates multiple transport adapters, routes incoming packets to the Zero Trust pipeline,
    and provides unified lifecycle controls.
    """

    def register_adapter(self, adapter: IIngestionAdapter) -> None:
        """Registers a new transport adapter into the hub."""
        ...

    def unregister_adapter(self, adapter_id: str) -> None:
        """Removes and stops a transport adapter by ID."""
        ...

    def get_adapter(self, adapter_id: str) -> Optional[IIngestionAdapter]:
        """Retrieves a registered adapter by ID."""
        ...

    def get_all_adapters(self) -> List[IIngestionAdapter]:
        """Returns a list of all currently registered adapters."""
        ...

    def start_all(self) -> None:
        """Starts all registered adapters."""
        ...

    def stop_all(self) -> None:
        """Stops all registered adapters."""
        ...

    def route_packet(self, source_id: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Routes an inbound packet into the Zero Trust pipeline.
        Returns True if accepted and authenticated by the pipeline.
        """
        ...

    def check_poll(self, current_time: float) -> None:
        """Delegates periodic polling checks to all registered polling adapters."""
        ...
