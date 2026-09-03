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
# File: src/interfaces/sensor_gateway.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class IPayloadParser(Protocol):
    """
    Contract for telemetry payload parsers (SRP & Strategy).
    Each implementation handles a single content-type or structure.
    """

    def can_parse(self, content_type: str, raw_body: str) -> bool:
        """Determines if this parser handles the given content type or body structure."""
        ...

    def parse(self, raw_body: str) -> Optional[Dict[str, Any]]:
        """Parses the raw body into a normalized Python dictionary."""
        ...


@runtime_checkable
class IPolyglotPayloadParser(Protocol):
    """Contract for registry and dispatcher of multiple payload parsers."""

    def register_parser(self, parser: IPayloadParser, priority: int = 0) -> None:
        """Registers a parser strategy with optional priority."""
        ...

    def parse(self, content_type: str, raw_body: str) -> Dict[str, Any]:
        """Dispatches parsing to the first matching strategy."""
        ...


@runtime_checkable
class ISensorIdExtractor(Protocol):
    """
    Contract for sensor identifier discovery and normalization heuristics.
    """

    def extract(self, payload: Any, client_ip: str, request_path: str = "") -> str:
        """Extracts and resolves the canonical sensor identifier."""
        ...

    def normalize_id(self, raw_id: str) -> str:
        """Normalizes raw identifier representations."""
        ...


@runtime_checkable
class ISensorGateway(Protocol):
    """
    Contract for sensor gateway orchestrator (Facade).
    """

    def start(self) -> None:
        """Starts the gateway server."""
        ...

    def stop(self) -> None:
        """Stops the gateway server."""
        ...

    def is_running(self) -> bool:
        """Returns whether the gateway is currently active."""
        ...

    def register_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Registers an event listener callback for received sensor data."""
        ...
