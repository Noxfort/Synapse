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
# File: src/infrastructure/sensor_gateway.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from src.infrastructure.parsers import (
    BasePayloadParser,
    CsvPayloadParser,
    IPayloadParser,
    JsonPayloadParser,
    PolyglotPayloadParser,
    RawFallbackPayloadParser,
    XmlPayloadParser,
    create_default_parser_registry,
)
from src.infrastructure.sensor_id_extractor import SensorIdExtractor
from src.interfaces.sensor_gateway import IPolyglotPayloadParser, ISensorGateway, ISensorIdExtractor
from src.utils.logging_setup import get_logger

logger = get_logger("SensorGateway")


# Global parser registry instance for backward compatibility
global_parser_registry = create_default_parser_registry()


# =============================================================================
# HTTP SERVER & PROTOCOL HANDLER (Infrastructure Layer - SRP / DIP)
# =============================================================================

class SensorHTTPServer(HTTPServer):
    """
    HTTP Server holding explicit instance reference to the orchestrator gateway.
    Eliminates class-level monkey patching and global static coupling.
    """
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, gateway: 'SensorGateway'):
        super().__init__(server_address, RequestHandlerClass)
        self.gateway: 'SensorGateway' = gateway


class IngestionHandler(BaseHTTPRequestHandler):
    """
    Pure HTTP Ingestion Request Handler (SRP).
    Focuses exclusively on HTTP protocol handling and delegates orchestration
    to the injected gateway attached to the server instance.
    """

    server: SensorHTTPServer

    def do_POST(self):
        """Receives data packets via POST on any endpoint and delegates to gateway."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty Request Body")
                return

            raw_body = self.rfile.read(content_length)
            decoded_body = raw_body.decode('utf-8', errors='ignore').strip()
            content_type = self.headers.get('Content-Type', '').lower()
            client_ip = self.client_address[0] if self.client_address else "127_0_0_1"

            # Delegate packet orchestration to the gateway instance via server context
            if hasattr(self.server, 'gateway') and self.server.gateway is not None:
                self.server.gateway.handle_inbound_request(
                    content_type=content_type,
                    decoded_body=decoded_body,
                    client_ip=client_ip,
                    request_path=self.path,
                    content_length=content_length,
                )

            # Response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "queued"}')

        except Exception as e:
            logger.error(f"❌ [SensorGateway] Ingestion Error: {e}", exc_info=True)
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        """Suppress default HTTP logging to keep console clean."""
        pass


# =============================================================================
# SENSOR GATEWAY FACADE & ORCHESTRATOR (SOLID Architecture)
# =============================================================================

class SensorGateway(QObject):
    """
    The Inbound Sensor Gateway (Facade & Orchestrator).
    
    SOLID Architecture:
    - [SRP] Exclusively coordinates ingestion lifecycle, parser dispatching, ID resolution, and data emission.
    - [OCP] Open for custom parsers and ID extractors via dependency injection.
    - [LSP] Conforms structurally to ISensorGateway protocol.
    - [ISP] Replaces heavy QThread inheritance with composed background thread execution.
    - [DIP] Decoupled from static globals; supports both pure Python callbacks and Qt signals.
    """

    # Qt Inbound Signals (Sensor -> Synapse Runtime)
    data_received = pyqtSignal(str, object)
    server_started = pyqtSignal(int)
    server_error = pyqtSignal(str)

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8080,
        parser_registry: Optional[IPolyglotPayloadParser] = None,
        id_extractor: Optional[ISensorIdExtractor] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.host = host
        self.port = port
        self._parser_registry: IPolyglotPayloadParser = parser_registry or create_default_parser_registry()
        self._id_extractor: ISensorIdExtractor = id_extractor or SensorIdExtractor()

        self._httpd: Optional[SensorHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._listeners: List[Callable[[str, Dict[str, Any]], None]] = []

    # =========================================================================
    # FACADE ORCHESTRATION PIPELINE
    # =========================================================================

    def register_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Allows pure Python subscribers to receive sensor packets without Qt signal dependencies."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Removes a registered callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def handle_inbound_request(
        self,
        content_type: str,
        decoded_body: str,
        client_ip: str,
        request_path: str,
        content_length: int,
    ) -> Dict[str, Any]:
        """
        Orchestration pipeline:
        1. Parse raw payload via polyglot strategy
        2. Identify device ID via extractor heuristic
        3. Notify Python listeners and emit Qt signals
        """
        # 1. Universal Parsing (Delegated Strategy)
        payload = self._parser_registry.parse(content_type, decoded_body)

        # 2. Identify Source (Delegated Extractor with URL path support)
        source_id = self._id_extractor.extract(payload, client_ip, request_path=request_path)

        # 3. Formatted Terminal Reception Log
        fmt_desc = content_type if content_type else "raw/auto"
        logger.info(
            f"📥 [SensorGateway] Recebido POST em '{request_path}' -> ID='{source_id}' (IP: {client_ip}) | "
            f"Formato: {fmt_desc} | Tamanho: {content_length} bytes"
        )

        # 4. Notify Listeners (Pure Callback Interface)
        for listener in self._listeners:
            try:
                listener(str(source_id), payload)
            except Exception as ex:
                logger.error(f"[SensorGateway] Error in packet listener: {ex}", exc_info=True)

        # 5. Emit RAW Payload to Engine (Thread-Safe Qt Signal)
        self.data_received.emit(str(source_id), payload)

        return payload

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    def start(self) -> None:
        """Starts the blocking HTTP Server in a background thread."""
        if self._is_running:
            logger.warning("[SensorGateway] Server is already running.")
            return

        self._is_running = True
        self._server_thread = threading.Thread(
            target=self._run_server,
            name=f"SensorGateway-HTTP-{self.port}",
            daemon=True,
        )
        self._server_thread.start()

    def _run_server(self) -> None:
        """Main Server Loop running in background thread."""
        try:
            self._httpd = SensorHTTPServer((self.host, self.port), IngestionHandler, gateway=self)
            self.server_started.emit(self.port)
            logger.info(f"📥 Listening for sensors on {self.host}:{self.port} (Polyglot Parsers Active)")

            while self._is_running and self._httpd:
                self._httpd.handle_request()

        except Exception as e:
            if self._is_running:
                self.server_error.emit(str(e))
                logger.error(f"Server Crash: {e}", exc_info=True)
        finally:
            self._is_running = False

    def stop(self) -> None:
        """Stops the server safely and releases network resources."""
        self._is_running = False
        if self._httpd:
            try:
                self._httpd.server_close()
            except Exception as e:
                logger.debug(f"[SensorGateway] Exception while closing server: {e}")
            self._httpd = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.0)
            self._server_thread = None

        logger.info("SensorGateway stopped.")

    def is_running(self) -> bool:
        """Returns True if the gateway server is actively listening."""
        return self._is_running

    def isRunning(self) -> bool:
        """Backward-compatible alias matching QThread API."""
        return self.is_running()

    def wait(self, timeout: Optional[float] = None) -> None:
        """Backward-compatible alias matching QThread.wait()."""
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=timeout)


__all__ = [
    "IPayloadParser",
    "BasePayloadParser",
    "JsonPayloadParser",
    "XmlPayloadParser",
    "CsvPayloadParser",
    "RawFallbackPayloadParser",
    "PolyglotPayloadParser",
    "create_default_parser_registry",
    "global_parser_registry",
    "SensorIdExtractor",
    "SensorHTTPServer",
    "IngestionHandler",
    "SensorGateway",
]
