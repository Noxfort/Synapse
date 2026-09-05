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
# File: src/services/telemetry_service.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Telemetry Service (SOLID: SRP & DIP).

Decouples telemetry lifecycle, MQTT reporting and shutdown flushes from controllers.
Implements ITelemetryService interface.
"""

import time
import logging
from typing import Optional

from PyQt6.QtCore import QCoreApplication
from src.infrastructure.monitor_client import MonitorClient
from src.interfaces.controllers import ITelemetryService

logger = logging.getLogger(__name__)


class TelemetryService(ITelemetryService):
    """
    Manages telemetry connections, incident reporting and graceful shutdown flushes.
    """

    def __init__(self, monitor_client: Optional[MonitorClient] = None):
        self._monitor_client: Optional[MonitorClient] = monitor_client

    @property
    def monitor_client(self) -> Optional[MonitorClient]:
        return self._monitor_client

    @property
    def enabled(self) -> bool:
        return self._monitor_client.enabled if self._monitor_client else False

    def init_telemetry(self, enabled: bool, host: str, port: int) -> None:
        """Initializes or restarts the background MonitorClient."""
        if self._monitor_client:
            try:
                self._monitor_client.stop()
            except Exception as e:
                logger.warning(f"[TelemetryService] Failed stopping previous monitor client: {e}")

        self._monitor_client = MonitorClient(host=host, port=port, enabled=enabled)
        logger.info(f"[TelemetryService] Telemetry configured (enabled={enabled}, host={host}:{port})")

    def reconfigure_telemetry(self, enabled: bool, host: str, port: int) -> None:
        """Reconfigures telemetry settings."""
        self.init_telemetry(enabled, host, port)

    def report_error(self, message: str) -> None:
        """Dispatches a critical software incident through the monitor client."""
        self.report_incident(category="SOFTWARE", level="CRITICAL", message=message)

    def report_incident(self, category: str, level: str, message: str) -> None:
        """Dispatches an incident report through the monitor client."""
        if self._monitor_client and self._monitor_client.enabled:
            try:
                self._monitor_client.report_incident(category=category, level=level, message=message)
            except Exception as e:
                logger.error(f"[TelemetryService] Error reporting incident: {e}")

    def report_shutdown(self) -> None:
        """
        Dispatches a shutdown event and waits briefly to allow the MQTT queue to flush.
        """
        if self._monitor_client and self._monitor_client.enabled:
            try:
                msg = QCoreApplication.translate("MainController", "System Shutdown Initiated")
                self._monitor_client.report_incident(category="SOFTWARE", level="CRITICAL", message=msg)
                # Blocking delay ensuring MQTT queue flush before process termination
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[TelemetryService] Error during shutdown telemetry report: {e}")
